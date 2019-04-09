#!/usr/bin/env python3.5

import argparse
import sys

from artiqDrivers.devices.arduinoDds.driver import ArduinoDds, ArduinoDdsSim
from artiq.protocols.pc_rpc import simple_server_loop
from artiq.tools import simple_network_args, init_logger
from oxart.tools import add_common_args


def get_argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--device", default=None,
                        help="serial device. See documentation for how to "
                             "specify a USB Serial Number.")
    parser.add_argument("--simulation", action="store_true",
                        help="Put the driver in simulation mode, even if "
                             "--device is used.")
    parser.add_argument("--clockfreq", default=1e9, type=float, help="clock frequency provided to DDS")
    
    simple_network_args(parser, 4003)
    add_common_args(parser)
    return parser


def main():
    args = get_argparser().parse_args()
    init_logger(args)

    if not args.simulation and args.device is None:
        print("You need to specify either --simulation or -d/--device "
              "argument. Use --help for more information.")
        sys.exit(1)

    if args.simulation:
        dev = ArduinoDdsSim()
    else:
        dev = ArduinoDds(addr=args.device, clockFreq=args.clockfreq)
        
    simple_server_loop({"arduinoDds": dev}, args.bind, args.port)


if __name__ == "__main__":
    main()
