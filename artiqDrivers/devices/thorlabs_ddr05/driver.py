import logging
import serial
import re
import sys
import asyncio
import thorlabs_apt as apt

import artiq.protocols.pyon as pyon

logger = logging.getLogger(__name__)


class Ddr05Driver:
    """Driver for Thorlabs Ddr05 motorised rotation mount"""
    def __init__(self, serial=None):
        dev_list = apt.list_available_devices()
        dev_sn_available = [dev[1] for dev in dev_list]

        if len(dev_list) == 0:
            raise Exception("No APT devices found")

        if serial is None: 
            serial = dev_sn_available[0]
        
        # Check serial number is present in available devices
        try:
            dev_sn_available.index(serial)
        except ValueError:
            raise ValueError("No device with serial number {} present (available = {})".format(serial, dev_sn_available))

        self.dev = apt.Motor(serial)

        # Motor must be homed after each power cycle of the controller
        # If the motor has already been homed this is fast
        self.dev.move_home(True)

    def set_angle(self, angle):
        """Set the motor angle in units of turns""" 
        angle %= 1
        self.dev.move_to(angle, blocking=True)

    def get_angle(self):
        """Returns the current motor angle in units of turns"""
        return self.dev.position

    def ping(self):
        return True