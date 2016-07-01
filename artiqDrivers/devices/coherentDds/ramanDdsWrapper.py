from artiq.language.core import *
from artiqRoutines.hfQubitTransitionFreq import HfQubitTransitionFreq


class RamanDdsWrapper:
    """Wraps a CoherentDDS class to allow profiles to be set in logical frequencies (detunings from zero field) rather than the physical frequencies that are the input to the Raman AOMs.
    This class is very ugly at the moment as it hardcodes the arrangement of our AOM (inc. the diffraction orders)."""
    def __init__(self, dmgr, device):
        """LO_freq : blue beat note frequency between master and slave laser"""
        self.core = dmgr.get("core")

        self.dds = dmgr.get(device)
        
        self.hfq = HfQubitTransitionFreq()
        
        self.msDiff = 3.2e9 # master-slave Raman laser frequency difference
        self.trans = 't4030' # hyperfine transition without Zeeman shift
        self.hfs = self.hfq.df_trans(B=0,mF4=int(self.trans[2]),mF3=int(self.trans[4])) # hyperfinesplitting, independent of B
        self.rH_freq = -109e6 # frequency of Rh, is -1st order
        
        # range of sensible frequencies for rPara and rV        
        self.rParaRange = [70e6,120e6]
        self.rVRange = [105e6,113e6]
    

    def setProfile(self, channel, profile, freq, phase=0.0, amp=1.0, addQubitFreq = True):
        ''' channnel: rPara or rV, profile: 0...7, if addQubitFreq=True: the lasers used to create the frequency difference are split by 3.2GHz '''
        if addQubitFreq:
            freqDDS = self.msDiff+self.rH_freq-freq
        else:
            freqDDS = freq - self.rH_freq
        
        if channel == 'rPara':
            # rPara is double passed +1,+1
            freqDDS /= 2
            phase /= 2
            if (freqDDS<self.rParaRange[0]) or (freqDDS>self.rParaRange[1]):
                raise ValueError("Rpara frequency out of range, {:.0f}MHz not in [{:.0f},{:.0f}]MHz".format(freqDDS/1e6,self.rParaRange[0]/1e6,self.rParaRange[1]/1e6))
            else:
                self.dds.setProfile(0, profile, freqDDS, phase=phase, amp=amp)
            
        elif channel == 'rV':
            # rV is -1st order  
            freqDDS *= -1     
            if (freqDDS<self.rVRange[0]) or (freqDDS>self.rVRange[1]):
                raise ValueError("Rpara frequency out of range, {:.0f}MHz not in [{:.0f},{:.0f}]MHz".format(freqDDS/1e6,self.rVRange[0]/1e6,self.rVRange[1]/1e6))
            else:
                self.dds.setProfile(1, profile, freqDDS, phase=phase, amp=amp)
            
        else:
            raise ValueError("Channel can only be rPara or rV")
            
        self.dds.resetPhase()
