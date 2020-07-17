#!/usr/bin/env python3.5

import argparse

from artiqDrivers.devices.bStabBb.bStabBb import BStabBb
from sipyco.pc_rpc import simple_server_loop
from artiq.tools import simple_network_args, init_logger
from oxart.tools import add_common_args


def get_argparser():
    parser = argparse.ArgumentParser()
    simple_network_args(parser, 4011)
    add_common_args(parser)
    return parser


def main():
    args = get_argparser().parse_args()
    init_logger(args)
    dev = BStabBb()
    simple_server_loop({"bStabBb": dev}, args.bind, args.port)


if __name__ == "__main__":
    main()
