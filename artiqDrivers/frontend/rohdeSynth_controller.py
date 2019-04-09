#!/usr/bin/env python3.5

import argparse
import sys

from artiqDrivers.devices.rohdeSynth.driver import RohdeSynth
from artiq.protocols.pc_rpc import simple_server_loop
from artiq.tools import simple_network_args, init_logger
from oxart.tools import add_common_args


def get_argparser():
    parser = argparse.ArgumentParser(description="ARTIQ controller for the Rohde&Schwarz SMA100A synthesiser")
    parser.add_argument("-i", "--ipaddr", default=None,
                        help="IP address of synth")
    parser.add_argument("--simulation", action="store_true",
                        help="Put the driver in simulation mode, even if "
                             "--ipaddress is used.")

    simple_network_args(parser, 4004)
    add_common_args(parser)
    return parser


def main():
    args = get_argparser().parse_args()
    init_logger(args)

    if not args.simulation and args.ipaddr is None:
        print("You need to specify either --simulation or -i/--ipaddr "
              "argument. Use --help for more information.")
        sys.exit(1)

    if args.simulation:
        dev = RohdeSynthSim()
    else:
        dev = RohdeSynth(addr=args.ipaddr)

    try:
        simple_server_loop({"rohdeSynth": dev}, args.bind, args.port)
    finally:
        dev.close()

if __name__ == "__main__":
    main()
