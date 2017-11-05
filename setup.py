from setuptools import setup

scripts = [
    "bme_pulse_picker_timing_controller=artiqDrivers.frontend.bme_pulse_picker_timing_controller:main",
    "bStab_controller=artiqDrivers.frontend.bStab_controller:main",
    "coherentDds_controller=artiqDrivers.frontend.coherentDds_controller:main",
    "arduinoDds_controller=artiqDrivers.frontend.arduinoDds_controller:main",
    "trapDac_controller=artiqDrivers.frontend.trapDac_controller:main",
    "thorlabs_mdt69xb_controller=artiqDrivers.frontend.thorlabs_mdt69xb_controller:main",
    "rohdeSynth_controller=artiqDrivers.frontend.rohdeSynth_controller:main",
    "tti_ql355_controller=artiqDrivers.frontend.tti_ql355_controller:main",
    "scpi_synth_controller=artiqDrivers.frontend.scpi_synth_controller:main",
    "thorlabs_ddr05_controller=artiqDrivers.frontend.thorlabs_ddr05_controller:main",
    "N8241A_controller=artiqDrivers.frontend.N8241A_controller:main"
]

setup(name='artiqDrivers',
    version='0.1',
    packages=['artiqDrivers',
              'artiqDrivers.frontend',
              'artiqDrivers.devices',
              'artiqDrivers.devices.bStabBb',
              'artiqDrivers.devices.arduinoDds',
              'artiqDrivers.devices.bme_pulse_picker',
              'artiqDrivers.devices.coherentDds',
              'artiqDrivers.devices.dosDac',
              'artiqDrivers.devices.rohdeSynth',
              'artiqDrivers.devices.thorlabs_mdt69xb',
              'artiqDrivers.devices.trapDac',
              'artiqDrivers.devices.tti_ql355',
              'artiqDrivers.devices.scpi_synth',
              'artiqDrivers.devices.thorlabs_ddr05',
              'artiqDrivers.profileSwitcher',
             ],
    entry_points={
        "console_scripts": scripts,
    },
    install_requires = [
        'pyserial>=3'
    ]
)
