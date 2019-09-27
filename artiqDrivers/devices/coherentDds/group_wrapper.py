from artiq.language.core import *
from artiq.language import us
import numpy as np
from artiq.coredevice import spi2

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

    def __init__(self, dmgr, devices, mappings, clock_div, invert=False):
        self.core = dmgr.get("core")

        self.invert = invert

        dds_devices = {}
        spi_devices = {}
        for (dds_name, spi_name) in devices:
            dds_devices[dds_name] = dmgr.get(dds_name)
            spi_devices[dds_name] = dmgr.get(spi_name) if spi_name else None

        ref_period_mu = self.core.seconds_to_mu(self.core.coarse_ref_period)
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

            channel_cls = DdsChannel(self.core, dds_dev, spi_dev, ch,\
                                    self._spi_write)
            setattr(self, channel, channel_cls)

    @kernel
    def _spi_write(self, spi, data, delay):
        if self.invert:
            spi.set_config_mu((spi2.SPI_END|spi2.SPI_CLK_POLARITY|spi2.SPI_CS_POLARITY), 8, 10, 1)
            # flags set: SPI_END sets cs to inactive at end of write, others do the inversion of everything but the signal
            # 8: 8bits, write length; 10: speed, division of clock speed by 10, can be anything >2, 1: initial state of cs, ie cs active
            spi.write(~(data<<24))
        else:
            spi.set_config_mu(spi2.SPI_END, 8, 10, 1)
            spi.write(data<<24)
        if delay:
            delay_mu(self.padding_mu+self.profile_delay_mu)


class DdsChannel:
    kernel_invariants = {"spi", "ch"}
    def __init__(self, core, device, spi, channel, _spi_write):
        self.core = core
        self.dev = device
        self.spi = spi
        self.ch = channel
        self._spi_write = _spi_write

    def set(self, frequency, profile=0, amplitude=1, phase=0):
        self.dev.setProfile(self.ch, profile, \
                            frequency, amp=amplitude, phase=phase)

        self.dev.resetPhase()

    def set_sensible_pulse_shape(self, duration):
        self.dev.setSensiblePulseShape(duration,self.ch)

    def get_lsb_freq(self):
        return self.dev.get_lsb_freq()

    def identity(self):
        idn = self.dev.identity()
        return idn

    def serial_reset_phase(self):
        self.dev.resetPhase()

    @kernel
    def use_profile(self, profile,delay = True):
        # write via SPI
        self._write_profile_select(self.spi, self.ch, profile, delay = delay)

    @kernel
    def pulse_enable(self,enable):
        # write via SPI
        self._write_pulse_enable(self.spi,self.ch,enable)

    @kernel
    def reset_phase(self):
        # write via SPI
        self._write_reset_phase(self.spi)

    @kernel
    def _write_profile_select(self, spi, ch, profile,delay = True):
        """Set the profile select for a given spi device and channel number."""
        # Wire format:
        # cs low, clock in 8 bit word, cs high
        # bits 7-6 : mode, 0=set profile select, 1=set pulse enable
        # bits 5-4 : channel, 0-3 for DDS channel 0-3
        # bits 3-0 : mode dependant data
        # if mode=0 : data[2:0] is the profile select vector
        # if mode=1 : data[0] is the pulse enable line
        # The DDS control signals take effect on the rising edge of cs.

        data = 0 << 6
        data += (ch & 3) << 4
        data += profile & 7
        self._spi_write(spi,data,delay = delay)

    @kernel
    def _write_pulse_enable(self, spi, ch, enable):
        """Set the profile select for a given spi device and channel number."""
        # Wire format:
        # cs low, clock in 8 bit word, cs high
        # bits 7-6 : mode, 0=set profile select, 1=set pulse enable
        # bits 5-4 : channel, 0-3 for DDS channel 0-3
        # bits 3-0 : mode dependant data
        # if mode=0 : data[2:0] is the profile select vector
        # if mode=1 : data[0] is the pulse enable line
        # The DDS control signals take effect on the rising edge of cs.

        data = 1 << 6
        data += (ch & 3) << 4
        data += enable & 1
        self._spi_write(spi,data,delay = False)

    @kernel
    def _write_reset_phase(self, spi):
        """Set the profile select for a given spi device and channel number."""
        # Wire format:
        # cs low, clock in 8 bit word, cs high
        # bits 7-6 : mode, 0=set profile select, 1=set pulse enable
        # bits 5-4 : channel, 0-3 for DDS channel 0-3
        # bits 3-0 : mode dependant data
        # if mode=0 : data[2:0] is the profile select vector
        # if mode=1 : data[0] is the pulse enable line
        # The DDS control signals take effect on the rising edge of cs.

        data = 2 << 6
        self._spi_write(spi,data,delay = True)