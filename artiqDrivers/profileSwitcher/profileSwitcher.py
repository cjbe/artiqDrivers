from artiq.language.core import *
from artiq.language.units import *
import numpy as np


class ProfileSwitcher:
    def __init__(self, dmgr, profile_lines, interProfileDelay=200*ns, finalDelay=200*ns):
        """interProfileDelay is the delay to insert between switching profile lines.
        finalDelay is the delay to add after all profile changes have occured.
        Profile line order is [p0, p1, p2]"""
        self.core = dmgr.get("core")
        
        self.nProfiles = len(profile_lines)
        self.profiles = []
        for ii, p0 in enumerate(profile_lines):
            self.profiles.append(dmgr.get(p0))
        self.interProfileDelay_mu = interProfileDelay
        self.finalDelay_mu = finalDelay
        

        
    @kernel
    def setProfile(self, profile):
        if profile < 0 or profile > (2**self.nProfiles)-1:
            raise InvalidProfile()
        
        for ii in range(self.nProfiles):
            if profile & 2**ii:
                self.profiles[ii].on()
            else:
                self.profiles[ii].off()
            delay(self.interProfileDelay_mu)
        delay(self.finalDelay_mu) 


class InvalidProfile(Exception):
    pass
