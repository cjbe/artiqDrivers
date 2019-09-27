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
    def __init__(self,name,freq_range,order,dds,dds2=None):
        self.rV_freq = 217.368555e6 # self.ms_diff+self.rH_freq-hfq.df_trans(mF4=4,mF3=3)
        self.ms_diff = 3.2e9 # master-slave Raman laser frequency difference
        self.rH_freq = -109e6 # frequency of Rh, is -1st order, =self.rV_freq+hfq.df_trans(mF4=4,mF3=3)-self.ms_diff
        self.rH2_freq = 217.309632e6 # frequency of Rh2, is +1st order, =self.rV_freq+hfq.df_trans(mF4=0,mF3=1)-self.ms_diff

        super().__init__(name,freq_range,order,dds,dds2=dds2)

    def calculate_dds_frequency(self,frequency,add_qubit_freq=True,on_clock=False):
        if self.name == 'rPara':
            if add_qubit_freq:
                if on_clock:
                    freqDDS = self.ms_diff+self.rH2_freq-frequency
                else:
                    freqDDS = self.ms_diff+self.rH_freq-frequency
            else: # this is used for gates, where the laser detuning is only the motional mode frequency + delta_g
            # works for both wobble and ms gate
                freqDDS = self.rV_freq + frequency
        elif self.name == 'rH2':
            freqDDS = self.rH2_freq
        elif self.name == 'rV':
            freqDDS = self.rV_freq
        else:
            raise ValueError("{} not a valid DDS channel name".format(self.name))
        return freqDDS


    def set(self, frequency, profile=0, amplitude=1, phase=0, add_qubit_freq=True, on_clock=False):
        freqDDS = self.calculate_dds_frequency(frequency,add_qubit_freq=add_qubit_freq,on_clock=on_clock)
        super().set(frequency=freqDDS, profile=profile, amplitude=amplitude, phase=phase)

    def set2(self, frequency, profile=0, amplitude=1, phase=0, add_qubit_freq=True, on_clock=False):
        freqDDS = self.calculate_dds_frequency(frequency,add_qubit_freq=add_qubit_freq,on_clock=on_clock)
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

        assert(dds._rPara.get_lsb_freq() == dds._rV.get_lsb_freq() == dds._rH2.get_lsb_freq() == dds._rParaB.get_lsb_freq()) #4 channels of the same DDS. Sanity check, set up in device db
        self.lsb = dds._rPara.get_lsb_freq()

        #self.rPara = AOM("rPara",[140e6, 250e6],+1,dds._rPara) # BW 40 MHz, single pass +1 order
        self.rPara = RamanAOM("rPara",[200e6, 250e6],+1,dds._rPara,dds2=dds._rParaB)
        self.rH2 = RamanAOM("rH2",[175e6, 225e6],+1,dds._rH2) # single pass +1 order
        self.rV = RamanAOM("rV",[175e6, 225e6],+1,dds._rV)

        #self.total_sp_amp = 0.35 #Old value so that we don't see higher harmonics when driving with 2 tones
        self.total_sp_amp = 1 # Gets more optical power


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
        self.rV.dds.reset_phase()

    def serial_reset_phase(self):
        self.rPara.dds.serial_reset_phase()
        self.rH2.dds.serial_reset_phase()
        self.rV.dds.serial_reset_phase()

    def _lsb_round(self,freq):
        """Rounds to nearest LSB freq of the DDS, i.e. the actual frequency produced by the DDS. """
        return int(round(freq/self.lsb))*self.lsb

    def set_profile(self, channel, frequency, profile=1, amplitude=1, phase=0, add_qubit_freq=True, on_clock=False):
        """Set profile"""
        if channel == 'rPara':
            self.rPara.set(frequency,profile=profile, amplitude=amplitude, phase=phase, add_qubit_freq=add_qubit_freq, on_clock=on_clock)
            self.rPara.identity()

        elif channel == 'rH2':
            self.rH2.set(frequency,profile=profile, amplitude=amplitude, phase=phase)
            self.rH2.identity()

        elif channel == 'rV':
            self.rV.set(frequency,profile=profile, amplitude=amplitude, phase=phase)
            self.rV.identity()


    def make_safe(self):
        """Prevents second channel connected to bichromatic AOM outputting RF, which may cause total RF power to exceed the AOM's damage threshold"""
        for i in range(8):
            self.rPara.set2(0, profile = i, amplitude = 0)
        self.rPara.set(0, profile = 1, amplitude = 0)


    def set_sensible_pulse_shape(self,pulse_shape_duration=2*us):
        self.rH2.dds.set_sensible_pulse_shape(pulse_shape_duration) #takes about 200ms
        self.rH2.identity()

    @kernel
    def pulse_shape_on(self):
        self.rH2.dds.pulse_enable(1)

    @kernel
    def pulse_shape_pulse(self,t):
        self.pulse_shape_on()
        delay(t)
        self.pulse_shape_off()

    @kernel
    def pulse_shape_off(self):
        self.rH2.dds.pulse_enable(0)

    def set_bichromat(self,sideband_freq, phase = 0, rPara_profile=1,
                      rParaB_profile=0, RSB_amp = None, BSB_amp = None):
        """Sets up the dds channels to output a symmetric bi-chromatic tone on the rPara AOM"""

        imbalance_param = 1.00

        RSB_amp_default = (imbalance_param/np.sqrt(2))*self.total_sp_amp
        BSB_amp_default = np.sqrt(1 - (imbalance_param**2)/2)*self.total_sp_amp

        RSB_amp = RSB_amp_default if RSB_amp is None else RSB_amp
        BSB_amp = BSB_amp_default if BSB_amp is None else BSB_amp

        assert(np.sqrt(RSB_amp**2 + BSB_amp**2) <= 1.0)

        self.rPara.set ( sideband_freq,profile=rPara_profile,  amplitude = BSB_amp, phase=phase, add_qubit_freq=False) #BSB
        self.rPara.set2(-sideband_freq,profile=rParaB_profile, amplitude = RSB_amp, phase=phase, add_qubit_freq=False) #RSB

        self.rPara.identity() # check if finished

