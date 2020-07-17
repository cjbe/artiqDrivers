#!/usr/bin/env python3.5

import argparse
import sys

from artiqDrivers.devices.trapDac.driver import TrapDac
from sipyco.pc_rpc import simple_server_loop
from sipyco.common_args import simple_network_args, init_logger
from oxart.tools import add_common_args


def get_argparser():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trapDacDevice", default=None,
                        help="Trap DC Dac serial device")
    parser.add_argument("--trapRFDevice", default=None,
                        help="Trap RF serial device")    
    
    simple_network_args(parser, 4005)
    add_common_args(parser)
    return parser


def main():
    args = get_argparser().parse_args()
    init_logger(args)

    if args.trapDacDevice is None or args.trapRFDevice is None:
        print("You need to specify --trapDacDevice and --trapRFDevice"
              "arguments. Use --help for more information.")
        sys.exit(1)

    dev = TrapDac(addr_dc_iface=args.trapDacDevice, addr_rf_iface=args.trapRFDevice)
        
    simple_server_loop({"trapDac": dev}, args.bind, args.port)


if __name__ == "__main__":
    main()
