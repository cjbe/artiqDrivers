#!/usr/bin/env python3.5

import argparse
import sys

from artiqDrivers.devices.tti_ql355.driver import QL355
from artiq.protocols.pc_rpc import simple_server_loop
from artiq.tools import verbosity_args, simple_network_args, init_logger, bind_address_from_args

def get_argparser():
    parser = argparse.ArgumentParser(description="ARTIQ controller for TTI QL355P (TP) single (triple) channel power supplies")
    simple_network_args(parser, 4006)
    parser.add_argument("-d", "--device", default=None,
                        help="serial device. See documentation for how to "
                             "specify a USB Serial Number.")
    verbosity_args(parser)
    return parser


def main():
    args = get_argparser().parse_args()
    init_logger(args)

    if args.device is None:
        print("You need to specify a -d/--device "
              "argument. Use --help for more information.")
        sys.exit(1)

    dev = QL355(args.device)

    # Q: Why not use try/finally for port closure?
    # A: We don't want to try to close the serial if sys.exit() is called,
    #    and sys.exit() isn't caught by Exception
    try:
        simple_server_loop({"ql355": dev}, bind_address_from_args(args), args.port)
    except Exception:
        dev.close()
    else:
        dev.close()
        
if __name__ == "__main__":
    main()
