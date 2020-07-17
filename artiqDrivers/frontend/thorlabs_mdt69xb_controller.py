#!/usr/bin/env python3.5

import argparse
import sys

from artiqDrivers.devices.thorlabs_mdt69xb.driver import PiezoController, SimulationPiezoController
from sipyco.pc_rpc import simple_server_loop
from sipyco.common_args import simple_network_args, init_logger_from_args
from oxart.tools import add_common_args

def get_argparser():
    parser = argparse.ArgumentParser(description="ARTIQ controller for the Thorlabs MDT693B or MDT694B 3 (1) channel open-loop piezo controller")
    simple_network_args(parser, 4002)
    parser.add_argument("-d", "--device", default=None,
                        help="serial device. See documentation for how to "
                             "specify a USB Serial Number.")
    parser.add_argument("--simulation", action="store_true",
                        help="Put the driver in simulation mode, even if "
                             "--device is used.")
    add_common_args(parser)
    return parser


def main():
    args = get_argparser().parse_args()
    init_logger_from_args(args)

    if not args.simulation and args.device is None:
        print("You need to specify either --simulation or -d/--device "
              "argument. Use --help for more information.")
        sys.exit(1)

    if not args.simulation:
        dev = PiezoController(args.device)
    else:
        dev = SimulationPiezoController()

    # Q: Why not use try/finally for port closure?
    # A: We don't want to try to close the serial if sys.exit() is called,
    #    and sys.exit() isn't caught by Exception
    try:
        simple_server_loop({"piezoController": dev}, args.bind, args.port)
    except Exception:
        dev.close()
    else:
        dev.close()
    finally:
        dev.save_setpoints()
        
if __name__ == "__main__":
    main()
