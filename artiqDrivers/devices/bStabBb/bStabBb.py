from Adafruit_BBIO.SPI import SPI
from Adafruit_BBIO import GPIO
#from artiq.language.core import *

class BStabBb:
  
    def __init__(self, coarsePin="P9_15", finePin="P9_16", readPin="P9_14", clockRate=100000):
        self.CS_FB_COARSE_PIN = coarsePin
        self.CS_FB_FINE_PIN = finePin
        self.CS_ADC_PIN = readPin
        self.FB_CLK_RATE = clockRate
        
        GPIO.setup(self.CS_FB_COARSE_PIN, GPIO.OUT)
        GPIO.setup(self.CS_FB_FINE_PIN, GPIO.OUT)
        self.spi00 = SPI(0,0)
        self.spi00.msh = self.FB_CLK_RATE
        
        #self.core = dmgr.get("core")
        #self.bbb = dmgr.get(device)
    
        
    def set_DAC_values(self,CDAC=-1,FDAC=-1):
        ''' this is the external function to be called for setting the coarse and fine dac '''
        if CDAC is not -1:
            self._set_coarse_dac(CDAC)
        if FDAC is not -1:
            self._set_fine_dac(FDAC)

    def read_voltage(self,verbose=0):
        ''' this is the external function to be called for reading out the ADC voltage '''
        # for AD7477:
        # 2 bytes
        bytes = self._read_value(self.CS_ADC_PIN, 2)
        # most significant bit first
        num = bytes[0] * 256 + bytes[1]
        # 4 leading zeros, 2 trailing zeros
        num = num >> 2
        # 5V reference, 10 bits
        AV = 5.0 * num / 1024
        
        # G=0.33 for voltage divider between shunt and ADC
        # convert to feedback shunt input voltage
        FB_SHNT_IN_V = 3 * AV
        
        if verbose:
            print("byte response: %X %X"% (bytes[0], bytes[1]))
            print("num respose: %d" % (num))
            print("ADC input voltage: %.2f" % (AV))
            print("Feedback shunt input voltage: %.2f" % (FB_SHNT_IN_V))
        
        return AV
    
    def test_set_pin(self,logicHigh=1,pin="P8_14"):
        ''' this is a test function to set a pin on the beaglebone to high/low '''
        GPIO.setup(pin, GPIO.OUT)
        if logicHigh:
            GPIO.output(pin, GPIO.HIGH)
        else:
            GPIO.output(pin, GPIO.LOW)
    
    def _set_coarse_dac(self,value):
        self._set_dac_value(self.CS_FB_COARSE_PIN, value)

    def _set_fine_dac(self,value):
        self._set_dac_value(self.CS_FB_FINE_PIN, value)
    
    def _set_dac_value(self, cs_pin, value):
        GPIO.output(cs_pin, GPIO.LOW)
        
        value = self._check_dac_value(value)
        
        # check if value is in range
        MSByte = value >> 8
        LSByte = value - (MSByte << 8)
        # write
        self.spi00.writebytes([MSByte,LSByte])
        
        GPIO.output(cs_pin, GPIO.HIGH)
        
    def _check_dac_value(self,value):
        value = int(value)
        if value > 65535:
            value = 65535
        if value < 0:
            value = 0
        return value
    
    def _read_value(self,cs_pin, length):
        ''' internal read value of analogue voltage '''
        GPIO.output(cs_pin, GPIO.LOW)
        
        bytes = self.spi00.readbytes(length)
        
        GPIO.output(cs_pin, GPIO.HIGH)
        return bytes

    def ping(self):
        return True

