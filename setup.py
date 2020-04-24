from setuptools import setup, find_packages

scripts = [
    "bme_pulse_picker_timing_controller=artiqDrivers.frontend.bme_pulse_picker_timing_controller:main",
    "bStab_controller=artiqDrivers.frontend.bStab_controller:main",
    "coherentDds_controller=artiqDrivers.frontend.coherentDds_controller:main",
    "arduinoDds_controller=artiqDrivers.frontend.arduinoDds_controller:main",
    "trapDac_controller=artiqDrivers.frontend.trapDac_controller:main",
    "rohdeSynth_controller=artiqDrivers.frontend.rohdeSynth_controller:main",
    "tti_ql355_controller=artiqDrivers.frontend.tti_ql355_controller:main",
    "scpi_synth_controller=artiqDrivers.frontend.scpi_synth_controller:main",
    "thorlabs_ddr05_controller=artiqDrivers.frontend.thorlabs_ddr05_controller:main",
    "N8241A_controller=artiqDrivers.frontend.N8241A_controller:main"
]

setup(name='artiqDrivers',
    version='0.1',
    packages=find_packages(),
    entry_points={
        "console_scripts": scripts,
    },
    install_requires = [
        'pyserial>=3'
    ]
)
