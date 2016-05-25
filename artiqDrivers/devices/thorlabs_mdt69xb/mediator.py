from artiq.language.core import *


class PiezoWrapper:
    """Wraps multiple piezo controllers to allow reference to channels by an easily remappable logical name.
    The arguments are 'devices', the list of piezo controllers, and 'mappings' is a dictionary mapping logical devices names to (device,channel) tuples"""
    def __init__(self, dmgr, devices, mappings):
        self.core = dmgr.get("core")
        self.devices = { dev: dmgr.get(dev) for dev in devices }
        
        self.mappings = mappings

    def set_channel(self, logicalChannel, value):
        # Look up device and channel
        (device, channel) = self._get_dev_channel(logicalChannel)

        # Set the physical device & channel to the given value
        device.set_channel(channel, value)

    def get_channel(self, logicalChannel):
        # Look up device and channel
        (device, channel) = self._get_dev_channel(logicalChannel)

        # Get physical device & channel value
        return device.get_channel(channel)

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
