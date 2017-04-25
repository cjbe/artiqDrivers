import time
import logging
import socket
import ctypes
import numpy as np


logger = logging.getLogger(__name__)


class N8241A:

    def __init__(self, addr):
        # addr : IP address of synth
        self.h = ctypes.CDLL("AGN6030A")
        
        resource_name = ctypes.c_char_p("TCPIP0::{}::inst0::INSTR".format(addr).encode())
        self.session = ctypes.c_uint(0)
        rc = self.h.AGN6030A_init(resource_name, ctypes.c_int(0), ctypes.c_int(1), ctypes.byref(self.session))

        if rc != 0:
            raise Exception("Could not connect")

        rc = self.h.AGN6030A_reset(self.session)
        assert(rc == 0)

        def setup_channel(channel):
            assert(channel >= 0 and channel <= 1)
            ch = ctypes.c_char_p(str(channel+1).encode())
            # Set to single-ended amplified operation, filter on, 500 MHz filter selected
            filter_en = 1
            rc = self.h.AGN6030A_ConfigureOutputConfiguration(self.session, ch, ctypes.c_int(2), ctypes.c_int(filter_en), ctypes.c_double(500e6))
            assert(rc == 0)

            # Set output to ON
            rc = self.h.AGN6030A_ConfigureOutputEnabled(self.session, ch, ctypes.c_int(1))
            assert(rc == 0)

        setup_channel(0)
        setup_channel(1)

        channel = ctypes.c_char_p("1".encode())

        # Select the Internal sample clock
        rc = self.h.AGN6030A_ConfigureSampleClock(self.session, 0, ctypes.c_double(1.25e9))
        assert(rc == 0)

        # Select the Internal reference clock
        rc = self.h.AGN6030A_ConfigureRefClockSource(self.session, 1)
        assert(rc == 0)

        # Operate in burst (vs continuous) mode, 1=burst, 0=continuous
        rc = self.h.AGN6030A_ConfigureOperationMode(self.session, channel, ctypes.c_int(0))
        assert(rc == 0)

        # Set to external trigger
        rc = self.h.AGN6030A_ConfigureTriggerSource(self.session, channel, ctypes.c_int(1))
        assert(rc == 0)

        # Set to run the ARB sequence once per trigger
        rc = self.h.AGN6030A_ConfigureBurstCount(self.session, channel, ctypes.c_int(1))
        assert(rc == 0)

        # Set N8241A output mode to ARB in preparation of downloading and playing our waveform.
        rc = self.h.AGN6030A_ConfigureOutputMode(self.session, ctypes.c_int(1))
        assert(rc == 0)

        # # Set N8241A to use external 10MHz reference input
        # rc = self.h.AGN6030A_ConfigureRefClockSource(self.session, ctypes.c_int(1))
        # assert(rc == 0)

        # Turn predistortion off to prevent attenuation of the signal
        predistort = ctypes.c_int(0)
        # Attribute ID magic numbers:
        # IVI_ATTR_BASE = 1000000
        # IVI_SPECIFIC_PUBLIC_ATTR_BASE = IVI_ATTR_BASE + 150000
        # AGN6030A_ATTR_PREDISTORTION_ENABLED (IVI_SPECIFIC_PUBLIC_ATTR_BASE + 28L)
        AGN6030A_ATTR_PREDISTORTION_ENABLED = ctypes.c_uint(1000000+150000+28)
        #Channel here needs to be NULL...
        rc = self.h.AGN6030A_SetAttributeViBoolean(self.session, ctypes.c_char_p(), AGN6030A_ATTR_PREDISTORTION_ENABLED, predistort)
        assert(rc == 0)


    def load_waveforms(self, wav_0=None, wav_1=None):
        """Load the waveforms for both channels. If a channels waveform is None
        a zero vector is loaded. Waveform length must be multiple of 16"""

        if wav_0 is None and wav_1 is None:
            print("None")
            raise Exception("No waveforms to program")

        if wav_0 is None:
            wav_0 = [0]*len(wav_1)
        if wav_1 is None:
            wav_1 = [0]*len(wav_0)

        # Download the waveform to both channels 1 and 2 even if 2 is not used.
        # This is a requirement of the N8241A interface. To do this, call the
        # function twice and discard the second waveform handle if Channel 2 is
        # not used.
        def load_waveform(waveform):
            # Waveform should be float values with abs <= 1
            n = len(waveform)
            DataType = n*ctypes.c_double
            data = DataType(*waveform)
            handle = ctypes.c_int()
            rc = self.h.AGN6030A_CreateArbWaveform(self.session,
                                                   ctypes.c_int(n),
                                                   data,
                                                   ctypes.byref(handle))
            assert(rc == 0)
            return handle

        def use_waveform(channel, handle):
            # Configure N8241A to play downloaded waveforms.
            # Set to 250mV gain and 0V offset.
            ch = ctypes.c_char_p(str(channel).encode())
            rc = self.h.AGN6030A_ConfigureArbWaveform(
                        self.session,
                        ch,
                        handle,
                        ctypes.c_double(0.5),
                        ctypes.c_double(0.0))
            assert(rc == 0)

        h1 = load_waveform(wav_0)
        h2 = load_waveform(wav_1)

        use_waveform(1, h1)
        use_waveform(2, h2)

    def ping(self):
        return True