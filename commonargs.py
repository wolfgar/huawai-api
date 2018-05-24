#!/usr/bin/env python2
#
# coding: utf-8
#

import logging
from huawei_api import HuaweiAPI


def get_huawei_from_args(parser):
    parser.add_argument("--user",
                        help="Username to log in",
                        default="admin",
                        required=False)
    parser.add_argument("--password",
                        help="password to log in",
                        required=True)
    parser.add_argument("--logfile",
                        help="Filename to save logs",
                        required=False)
    parser.add_argument("--loglevel",
                        help="loglevel",
                        required=False,
                        choices=["DEBUG", "INFO", "WARN", "ERROR"],
                        default="INFO")
    parser.add_argument("--ip",
                        help="Modem IP address",
                        default="192.168.8.1",
                        required=False)

    args = parser.parse_args()

    logging.getLogger().setLevel(getattr(logging, args.loglevel))
    api = HuaweiAPI(host=args.ip, user=args.user, passwd=args.password,
                    logfile=args.logfile)
    return (api, args)
