#!/usr/bin/env python3.5

import argparse
import sys

from artiqDrivers.devices.thorlabs_ddr05.driver import Ddr05Driver
from sipyco.pc_rpc import simple_server_loop
from artiq.tools import simple_network_args, init_logger
from oxart.tools import add_common_args

def get_argparser():
    parser = argparse.ArgumentParser(description="ARTIQ controller for the Thorlabs DDR05 motorised rotation mount")
    simple_network_args(parser, 4010)
    parser.add_argument("-s", "--serial", default=None,
                        help="serial number of device. Uses first device if not provided")
    add_common_args(parser)
    return parser


def main():
    args = get_argparser().parse_args()
    init_logger(args)

    dev = Ddr05Driver(serial=args.serial)

    simple_server_loop({"ddr05": dev}, args.bind, args.port)
        
if __name__ == "__main__":
    main()
