from artiq.language.core import *
from artiq.language.units import *
import numpy as np
import time



class AOM:
    """ Class which holds all the properties and funcitons of each AOM:

        range: useable frequency range
        centre: centre frequency
        order: sum of the orders of each pass (i.e. double pass both in -1 order is -2)
        ttl: ttl device switching RF to AOM (or at least one of the channels)
        dds: first channel connected to AOM
        dds2: second channel connected to AOM (if any)

        Tried to use namedtuple, but ran into compiler issues when terminating an experiment
    """
    def __init__(self,name,freq_range,order,dds,dds2=None):
        self.name  = name
        self.range = freq_range
        self.order = order
        self.dds = dds
        self.dds2 = dds2

    def _set_dds(self, frequency, profile, amplitude, phase,dds):

        freq_dds = frequency/self.order
        phase_dds = phase/self.order

        if self.range[0] <= freq_dds <= self.range[1]:
            dds.set(freq_dds, profile = profile, amplitude = amplitude, phase = phase_dds)
        else:
            raise ValueError("{} AOM frequency out of range, {:.0f}MHz not in [{:.0f},{:.0f}]MHz".format(self.name,freq_dds / 1e6, self.range[0] / 1e6, self.range[1] / 1e6))

    def set(self, frequency, profile=0, amplitude=1, phase=0):
        self._set_dds(frequency, profile=profile, amplitude=amplitude, phase=phase,dds=self.dds)

    def identity(self):
        idn = self.dds.identity()
        return idn

    def set2(self, frequency, profile=0, amplitude=1, phase=0):
        if self.dds2 == None:
            raise AttributeError("{} AOM does not have a second DDS channel".format(self.name))
        self._set_dds(frequency, profile=profile, amplitude=amplitude, phase=phase,dds=self.dds2)



class RamanAOM(AOM):
    def __init__(self,**kwargs):
        self.rV_freq = 217.368568e6
        self.ms_diff = 3.2e9 # master-slave Raman laser frequency difference
        self.rH_freq = -109e6 # frequency of Rh, is -1st order

        super().__init__()

    def calculate_dds_frequency(self,frequency):
        if self.name == 'rPara':
            if addQubitFreq:
                freqDDS = self.ms_diff+self.rH_freq-frequency
            else:
                freqDDS = self.rV_freq + frequency
        elif self.name == 'rH2':
            freqDDS = self.ms_diff+self.rH_freq-frequency
        elif self.name == 'rV':
            freqDDS = self.rV_freq
        else:
            raise ValueError("{} not a valid DDS channel name".format(self.name))
        return freqDDS


    def set(self, frequency, profile=0, amplitude=1, phase=0, addQubitFreq=True):
        freqDDS = calculate_dds_frequency(frequency)
        super().set(frequency=freqDDS, profile=profile, amplitude=amplitude, phase=phase)

    def set2(self, frequency, profile=0, amplitude=1, phase=0, addQubitFreq=True):
        freqDDS = calculate_dds_frequency(frequency)
        super().set2(frequency=freqDDS, profile=profile, amplitude=amplitude, phase=phase)




class RamanInterface:
    """
    Wrapper which allows logical frequencies offsets from the 674 carrier to
    be programmed without knowledge of the AOM order, and which abstracts away some of the implementation details of pulsing etc..
    This class hardcodes the AOM orders and arrangements
    The arguments are:
        'dds_device', DDS group_wrapper device
    """

    def __init__(self, dmgr, dds_device):

        dds = dmgr.get(dds_device)
        self.core = dmgr.get("core")

        assert(dds._rPara.get_lsb_freq() == dds._rV.get_lsb_freq() == dds._rH2.get_lsb_freq() == dds._rH2b.get_lsb_freq()) #4 channels of the same DDS. Sanity check, set up in device db
        self.lsb = dds._rPara.get_lsb_freq()

        #self.rPara = AOM("rPara",[140e6, 250e6],+1,dds._rPara) # BW 40 MHz, double pass -1 order
        self.rPara = AOM("rPara",[0e6, 401e6],+1,dds._rPara)
        self.rH2 = AOM("rH2",[175e6, 225e6],+1,dds._rH2,dds._rH2b) # BW 50 MHz, single pass -1 order . Here TTL switches second channel going to AOM, first channel is always on.
        self.rV = AOM("rV",[175e6, 225e6],+1,dds._rV)

        #self.total_sp_amp = 0.35 #Old value so that we don't see higher harmonics when driving with 2 tones
        self.total_sp_amp = 1 # Gets more optical power

        self.dds_delay = 200*ms#0#1*ms #Enough time to let the DDS update, program long pulseshapes, and hopefully prevent crashes

        self.pulse_shape_duration = 2*us

    @kernel
    def set_to_profile(self,channel,profile,delay=True):
        if channel == 'rPara':
            self.rPara.dds.use_profile(profile,delay = delay)
        elif channel == 'rH2':
            self.rH2.dds.use_profile(profile,delay = delay)


    @kernel
    def reset_phase(self):
        #TODO check, which channels/ simultaneously? we need to switch channels
        self.rPara.dds.reset_phase()
        self.rH2.dds.reset_phase()

    def _lsb_round(self,freq):
        """Rounds to nearest LSB freq of the DDS, i.e. the actual frequency produced by the DDS. """
        return int(round(freq/self.lsb))*self.lsb

    def set_profile(self, channel, frequency, profile=1, amplitude=1, phase=0):
        """Set profile"""
        if channel == 'rPara':
            self.rPara.set(frequency,profile=profile, amplitude=amplitude, phase=phase)
            #self.rPara.dds.set_sensible_pulse_shape(self.pulse_shape_duration)
            self.rPara.identity()

        elif channel == 'rH2':
            self.rH2.set(frequency,profile=profile, amplitude=amplitude, phase=phase)



    def make_safe(self):
        """Prevents second channel connected to SP AOM outputting RF, which may cause total RF power to exceed the AOM's damage threshold"""
        for i in range(8):
            self.rH2.set2(0, profile = i, amplitude = 0)
        self.rH2.set(0, profile = 1, amplitude = 0)

    @kernel
    def set_sensible_pulse_shape(self):
        self.rPara.dds.set_sensible_pulse_shape(self.pulse_shape_duration) #takes about 200ms

    @kernel
    def pulse_shape_on(self):
        self.rPara.dds.pulse_enable(1)

    @kernel
    def pulse_shape_off(self):
        self.rPara.dds.pulse_enable(0)

    # def set_bichromat(self,sideband_freq, phase = 0, centre_freq=0, RSB_amp = None, BSB_amp = None):
    #     """Sets up the dds channels to output a symmetric bicromatic tone on the SP AOM, with the DP AOM at the centre freq. This sets the DP profile 0 to "centre_freq" and "phase", and the SP first channel, profile 0 to it's centre """

    #     imbalance_param = 1.04

    #     RSB_amp_default = (imbalance_param/np.sqrt(2))*self.total_sp_amp
    #     BSB_amp_default = np.sqrt(1 - (imbalance_param**2)/2)*self.total_sp_amp

    #     RSB_amp = RSB_amp_default if RSB_amp is None else RSB_amp
    #     BSB_amp = BSB_amp_default if BSB_amp is None else BSB_amp

    #     assert(np.sqrt(RSB_amp**2 + BSB_amp**2) <= 1.0)

    #     self.dp.set(centre_freq,phase=phase) # set DP AOM at centre of bichromatic field on profile 0

    #     rounded_sideband_freq = self._lsb_round(sideband_freq) # To ensure RSB and BSB are not rounded differently

    #     assert(self._lsb_round(self.sp.centre) == (self._lsb_round(self.sp.centre+rounded_sideband_freq) + self._lsb_round(self.sp.centre-rounded_sideband_freq))/2 )

    #     self.sp.set(rounded_sideband_freq,profile=1, amplitude = BSB_amp) #BSB
    #     self.sp.set2(-rounded_sideband_freq,profile=0, amplitude = RSB_amp) #RSB
    #     self.dp.dds.set_sensible_pulse_shape(self.pulse_shape_duration)

        # time.sleep(self.dds_delay)

