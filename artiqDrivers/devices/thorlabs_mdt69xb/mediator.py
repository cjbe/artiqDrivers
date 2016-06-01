from artiq.language.core import *
import numpy as np
import time

class PiezoWrapper:
    """
    Wraps multiple piezo controllers to allow reference to channels by an
    easily remappable logical name. The arguments are:
        'devices', the list of piezo controllers,
        'mappings', a dictionary mapping logical devices names to
            (device,channel) tuples, and
        'slow_scan', a dictionary mapping the logical devices which require
            incremented voltage steps to the maximum step size in volts.
    """
    def __init__(self, dmgr, devices, mappings, slow_scan):
        self.core = dmgr.get("core")
        self.devices = { dev: dmgr.get(dev) for dev in devices }
        
        self.mappings = mappings
        self.slow_scan = slow_scan

    def set_channel(self, logicalChannel, value):
        # Look up device and channel
        (device, channel) = self._get_dev_channel(logicalChannel)

        # Set the physical device & channel to the given value
        if logicalChannel in self.slow_scan:
            step = self.slow_scan[logicalChannel]
            current = device.get_channel_setpoint(channel)
            if current < 0:
                # No information available on setpoint, skip slow setting
                # and hope
                # TODO: be better.
                pass
            else:
                sgn = np.sign(value - current)
                while abs(value - current) > step:
                    current += sgn*step
                    device.set_channel(channel, current)
                    time.sleep(0.01)
        device.set_channel(channel, value)

    def get_channel(self, logicalChannel):
        # Look up device and channel
        (device, channel) = self._get_dev_channel(logicalChannel)

        # Get physical device & channel value
        return device.get_channel(channel)

    def get_channel_setpoint(self, logicalChannel):
        # Look up device and channel
        (device, channel) = self._get_dev_channel(logicalChannel)

        # Get physical device & channel value
        return device.get_channel_setpoint(channel)

    def _get_dev_channel(self, logicalChannel):
        """Return a (device handle, channel) tuple given a logical channel"""
        # Look up the (device name, channel name) tuple in the mappings dictionary
        try:
            (deviceName,channel) = self.mappings[logicalChannel]
        except KeyError:
            raise UnknownLogicalChannel

        # Find the handle to the device class given by deviceName
        try:
            device = self.devices[deviceName]
        except KeyError:
            raise UnknownDeviceName

        return (device, channel)
        
        
class UnknownLogicalChannel(Exception):
    """The logical channel given was not found in the mappings dictionary"""
    pass

class UnknownDeviceName(Exception):
    """The device name for the given logical channel was not found in the devices list"""
    pass
