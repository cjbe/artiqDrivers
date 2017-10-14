from artiq.language.core import *
from artiq.language import us
import numpy as np


class DdsGroup:
    """
    Wraps multiple DDSs, each connected via a 'slow control' USB interface and
    optionally a realtime SPI bus for profile switching.
    The arguments are:
        'devices', tuples of DDS USB interface device, and SPI
            interface device or None,
        'mappings', a dictionary mapping logical devices names to
            (device,channel) tuples. The logical names must be valid python
            attribute names (e.g. cannot start with a number)

    This is a hacky interface. Profile 7 is reserved as an 'off' profile.
    It is programmed whenever profile 0 is written to with the same parameters
    but zero amplitude.

    We assume that the startup experiment has setup the SPI buses by calling
    set_xfer(1,8,0) and that the SPI clock_div is set to match the value in this
    class.
    """
    kernel_invariants = {"core", "profile_delay_mu", "padding_mu"}

    def __init__(self, dmgr, devices, mappings):
        self.core = dmgr.get("core")

        dds_devices = {}
        spi_devices = {}
        for (dds_name, spi_name) in devices:
            dds_devices[dds_name] = dmgr.get(dds_name)
            spi_devices[dds_name] = dmgr.get(spi_name) if spi_name else None
        mappings = mappings

        ref_period_mu = self.core.seconds_to_mu(self.core.coarse_ref_period)
        clock_div = 2 # This is set in the startup experiment
        write_period_mu = clock_div*ref_period_mu
        xfer_period_mu = 8*write_period_mu
        self.profile_delay_mu = self.core.seconds_to_mu(1.3*us) + \
                                    xfer_period_mu + write_period_mu
        self.padding_mu = xfer_period_mu + write_period_mu + ref_period_mu

        for channel in mappings:
            dev_name = mappings[channel][0]
            ch = mappings[channel][1]
            dds_dev = dds_devices[dev_name]

            spi_dev = spi_devices[dev_name]

            channel_cls = DdsChannel(self.core, dds_dev, spi_dev, ch, \
                                    self._write_profile_select)
            setattr(self, channel, channel_cls)

    @kernel
    def _write_profile_select(self, spi, ch, profile, add_padding_delay=True):
        """Set the profile select for a given spi device and channel number."""
        # Wire format:
        # cs low, clock in 8 bit word, cs high
        # bits 7-6 : mode, 0=set profile select, 1=set pulse enable
        # bits 5-4 : channel, 0-3 for DDS channel 0-3
        # bits 3-0 : mode dependant data
        # if mode=0 : data[2:0] is the profile select vector
        # if mode=1 : data[0] is the pulse enable line
        # The DDS control signals take effect on the rising edge of cs.
        data = 0
        data += (ch & 0xf) << 4
        data += profile & 0x7

        t0_mu = now_mu()
        at_mu(t0_mu - self.profile_delay_mu)
        spi.write(data<<24)
        at_mu(t0_mu)
        if add_padding_delay:
            delay_mu(self.padding_mu)




class DdsChannel:
    kernel_invariants = {"spi", "ch"}
    def __init__(self, core, device, spi, channel, _write_profile_select):
        self.core = core
        self.dev = device
        self.spi = spi
        self.ch = channel
        self._write_profile_select = _write_profile_select

    def set(self, frequency, profile=0, amplitude=1, phase=0):
        self.dev.setProfile(self.ch, profile, \
                            frequency, amp=amplitude, phase=phase)
        if profile == 0:
            self.dev.setProfile(self.ch, 7, \
                            frequency, amp=0)
        self.dev.resetPhase()

    @kernel
    def use_profile(self, profile):
        self._write_profile_select(self.spi, self.ch, profile)

    @kernel
    def on(self, profile=0):
        self.use_profile(profile)

    @kernel
    def off(self):
        self.use_profile(7)

