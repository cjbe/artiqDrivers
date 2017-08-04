from artiq.language.core import *


class QuadrupoleDdsWrapper():
    """Wrapper which allows logical frequencies offsets from the 674 carrier to
    be programmed without knowledge of the AOM order"""

    def __init__(self, dmgr, device):

        self.dds = dmgr.get(device)  # Gets the QuadruoleDds_raw device
        # Sensible frequency range for double pass AOM
        self.DP_AOM_range = [60e6, 100e6]
        self.SP_AOM_freq = 200e6

    def setProfile(self, channel, profile, freq, phase=0.0, amp=1.0, zero_freq = 80e6):
        """Sets profiles for channel 1, the double pass AOM only"""
        if channel != 'DP_AOM':
            raise ValueError(
                "This driver only allows the double pass AOM frequency to be changed")
        if profile not in {0, 1}:
            raise ValueError("Double pass AOM only has one profile select bit")

        freq_dds = zero_freq - 0.5 * freq  # Double pass Aom is in -1 order
        if self.DP_AOM_range[0] <= freq_dds <= self.DP_AOM_range[1]:
            self.dds.setProfile(1, profile, freq_dds, phase=phase, amp=amp)
        else:
            raise ValueError("DP AOM frequency out of range, {:.0f}MHz not in [{:.0f},{:.0f}]MHz".format(freq_dds / 1e6, self.DP_AOM_range[0] / 1e6, self.DP_AOM_range[1] / 1e6))

        self.dds.setProfile(0, 0, self.SP_AOM_freq)  # Setting the SP AOM freq
        self.dds.resetPhase()
