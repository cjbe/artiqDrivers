from artiq.language.core import *
import numpy as np
import time

class PsuWrapper:
    """
    Wraps multiple power supplies to allow reference to channels by an
    easily remappable logical name. The arguments are:
        'devices', the list of power supplies,
        'mappings', a dictionary mapping logical devices names to
            (device,channel) tuples
    """
    def __init__(self, dmgr, devices, mappings, slow_scan):
        self.core = dmgr.get("core")
        self.devices = { dev: dmgr.get(dev) for dev in devices }
        
        self.mappings = mappings

    def set_voltage_limit(self, logicalChannel, value):
        (device, channel) = self._get_dev_channel(logicalChannel)
        device.set_voltage_limit(value, channel=channel)

    def set_current_limit(self, logicalChannel, value):
        (device, channel) = self._get_dev_channel(logicalChannel)
        device.set_current_limit(value, channel=channel)

    def set_output_enable(self, logicalChannel, value):
        (device, channel) = self._get_dev_channel(logicalChannel)
        device.set_output_enable(value, channel=channel)

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
