from Adafruit_BBIO.SPI import SPI
from Adafruit_BBIO import GPIO
import artiq.protocols.pyon as pyon

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
        
        self.fname = "dacValues.pyon"

        self.maxDACvalue = (1<<16)-1
        
        # Ca43
        self.kHz_per_mG = -2.45
        # measured
        self.mG_per_mA = 146 / 56.64
        # (sensor+DiffAmp) equivalent : 6.06ohm
        # Verr: voltage of error signal
        self.mA_per_mVerr = 1 / 6.06

        self.mG_per_mVerr = self.mG_per_mA * self.mA_per_mVerr
        self.kHz_per_mVerr = self.kHz_per_mG * self.mG_per_mVerr

        # maximum DAC output: 2.048V
        self.mVDAC_per_DACvalue = 2.048e3 / self.maxDACvalue

        # estimates for the slope qubit_freq'(DACvalue)
        # fine DAC gain 1
        # coarse DAC gain 200
        self.kHz_per_fDACvalue_est = self.kHz_per_mG * self.mG_per_mVerr * self.mVDAC_per_DACvalue
        self.kHz_per_cDACvalue_est = self.kHz_per_mG * self.mG_per_mVerr * 200 * self.mVDAC_per_DACvalue
        
    def get_max_dac_value(self):
        return self.maxDACvalue
    
    def adjust_b_field(self, freq_diff, corrFactor=1):
        [cDAC, fDAC] = self.calcNewDACvaluesFromFreqDiff(freq_diff, corrFactor)
        self.setStabiliserDACs(cDAC, fDAC)
        
    def setStabiliserDACs(self, cDacValue, fDacValue, verbose=False):
        """Update feedback DAC values"""
        self.set_DAC_values(CDAC=cDacValue,FDAC=fDacValue)
        dacValues = {'cDAC':cDacValue,'fDAC':fDacValue}
        pyon.store_file(self.fname, dacValues)
        #self.set_dataset("BField_stabiliser.cDAC", float(cDacValue), persist=True, broadcast=True)
        #self.set_dataset("BField_stabiliser.fDAC", float(fDacValue), persist=True, broadcast=True)
        #if verbose:
        #    print("Update DACs {} {} --- Done.".format(int(cDacValue),int(fDacValue)))
        return dacValues

    def checkStabiliserOutput(self, volt_margin=3, verbose=False):
        """Read feedback shunt voltage via ssh connection"""
        shunt_ok = False
        shuntVoltage = self.read_voltage()

        #TODO check if this always works (what if V_shunt>10V?)
        shunt_voltage = float(shuntVoltage[-1][-4:])
        if shunt_voltage > (10-volt_margin):
            shunt_ok_msg = "Too high!"
        elif shunt_voltage < volt_margin:
            shunt_ok_msg = "Too low!"
        else:
            shunt_ok = True
            shunt_ok_msg = "Fine."
        if verbose:
            print("Read ADC --- Shunt input voltage: {} --- {}".format(shunt_voltage, shunt_ok_msg))
        # to do: raise Error when railing
        return shunt_ok
        
    def getSlopes(self):
        """Return conversion factors [cDAC_per_mG,fDAC_per_mG] """
        """Use for scanning the magnetic field"""
        # fine DAC gain 1
        # coarse DAC gain 200
        mG_per_fDACvalue = self.mG_per_mVerr * self.mVDAC_per_DACvalue
        mG_per_cDACvalue = self.mG_per_mVerr * 200 * self.mVDAC_per_DACvalue
        return {'cDAC_per_mG': 1.0/mG_per_cDACvalue,
                'fDAC_per_mG': 1.0/mG_per_fDACvalue}
        
        
    def calcNewDACvaluesFromFreqDiff(self, freq_diff, corrFactor=1):
        """Calculate new DAC values, based on the stretch qubit frequency difference to the setpoint"""
        # least significant bits in mV output
        fDAClsb = self.mVDAC_per_DACvalue
        # VERR = 200*cDAC + fDAC - 202*DIFF_SIG
        cDAClsb = 200 * fDAClsb
        
        VERR_diff = freq_diff / self.kHz_per_mVerr / 1e3
        VERR_corr = VERR_diff * corrFactor

        if abs(VERR_corr) > 10*cDAClsb:
            change_cDAC = - int(round(VERR_corr / cDAClsb))
            change_fDAC = 0
        else:
            change_cDAC = 0
            change_fDAC = - int(round(VERR_corr / fDAClsb))
        
        try:
            oldDacValues = pyon.load_file(self.fname)
            #old_cDAC = self.get_dataset("BField_stabiliser.cDAC")
            #old_fDAC = self.get_dataset("BField_stabiliser.fDAC")
        except FileNotFoundError:
            print('Error: could not find file. Using default values')
            oldDacValues = {'cDAC':54710,'fDAC':33354}
        old_cDAC = oldDacValues['cDAC']
        old_fDAC = oldDacValues['fDAC']
        
        new_cDAC = old_cDAC + change_cDAC
        new_fDAC = old_fDAC + change_fDAC
        
        # when fDAC out of range, change coarse DAC
        if (new_fDAC > self.maxDACvalue or new_fDAC < 0):
            new_cDAC += (new_fDAC-30000)/200
            new_fDAC = 30000
        
        return [new_cDAC, new_fDAC]
  
        
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
        ''' this is a test function to set a pin on the beaglebone to high or low '''
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

