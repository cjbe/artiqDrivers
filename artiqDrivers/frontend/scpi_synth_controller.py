#!/usr/bin/env python3.5

import argparse
import sys

from artiqDrivers.devices.scpi_synth.driver import ScpiSynth
from sipyco.pc_rpc import simple_server_loop
from artiq.tools import simple_network_args, init_logger
from oxart.tools import add_common_args


def get_argparser():
    parser = argparse.ArgumentParser(description="ARTIQ controller for SCPI synths")
    parser.add_argument("-i", "--ipaddr", default=None,
                        help="IP address of synth")

    simple_network_args(parser, 4004)
    add_common_args(parser)
    return parser


def main():
    args = get_argparser().parse_args()
    init_logger(args)

    if args.ipaddr is None:
        print("You need to specify -i/--ipaddr"
            "Use --help for more information.")
        sys.exit(1)

    dev = ScpiSynth(addr=args.ipaddr)

    try:
        simple_server_loop({"scpi_synth": dev}, args.bind, args.port)
    finally:
        dev.close()

if __name__ == "__main__":
    main()
