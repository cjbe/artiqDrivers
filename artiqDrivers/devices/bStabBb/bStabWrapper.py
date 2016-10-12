from artiq.experiment import *

class BStabWrapper:
    """Control of beaglebone in charge of coil current stabiliser DACs"""

    def __init__(self, dmgr, device):
        self.setattr_device("core")
        self.bStab = dmgr.get(device)

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
        
        
    def adjust_b_field(self, freq_diff, corrFactor=1):
        [cDAC, fDAC] = self.calcNewDACvaluesFromFreqDiff(freq_diff, corrFactor)
        self.setStabiliserDACs(cDAC, fDAC)
        
    def setStabiliserDACs(self, cDacValue, fDacValue, verbose=False):
        """Update feedback DAC values"""
        self.bStab.set_DAC_values(CDAC=cDacValue,FDAC=fDacValue)
        self.set_dataset("BField_stabiliser.cDAC", float(cDacValue), persist=True, broadcast=True)
        self.set_dataset("BField_stabiliser.fDAC", float(fDacValue), persist=True, broadcast=True)
        if verbose:
            print("Update DACs {} {} --- Done.".format(int(cDacValue),int(fDacValue)))

    def checkStabiliserOutput(self, volt_margin=3, verbose=False):
        """Read feedback shunt voltage via ssh connection"""
        shunt_ok = False
        shuntVoltage = self.bStab.read_voltage()

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
        
        old_cDAC = self.get_dataset("BField_stabiliser.cDAC")
        old_fDAC = self.get_dataset("BField_stabiliser.fDAC")
        
        new_cDAC = old_cDAC + change_cDAC
        new_fDAC = old_fDAC + change_fDAC
        
        # when fDAC out of range, change coarse DAC
        if (new_fDAC > self.maxDACvalue or new_fDAC < 0):
            new_cDAC += (new_fDAC-30000)/200
            new_fDAC = 30000
        
        return [new_cDAC, new_fDAC]

    def test_set_pin(self,logicHigh=1,pin="P8_14"):
        bStab.test_set_pin(logicHigh=logicHigh,pin=pin)
