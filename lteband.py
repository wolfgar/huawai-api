#!/usr/bin/env python2
#
# coding: utf-8
#

from huawei_api import HuaweiAPI
import logging
import argparse
import sys
import time

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Enable or Disable a FDD Band",
                                     epilog="This tool allows to enable or "
                                     "disable a LTE band for some Huawei modems")
    parser.add_argument("--enable",
                        help="Band number to enable",
                        required=False)
    parser.add_argument("--disable",
                        help="Band number to disable",
                        required=False)
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
    if not args.enable and not args.disable:
        print "A band to be enabled or disabled has to be set"
        sys.exit(-1)
    if args.enable:
        b = int(args.enable)
    else:
        b = int(args.disable)

    logging.getLogger().setLevel(getattr(logging, args.loglevel))
    log = logging.getLogger("lteband")
    api = HuaweiAPI(host=args.ip, user=args.user, passwd=args.password,
                    logfile=args.logfile)
    # Check whether the BAND is supported by the modem
    band_list = api.net_mode_list()
    log.info("The Modem supports the following LTE bands: " +
             band_list['LTEBandList']['LTEBand'][0]["Name"])
    if (int(band_list['LTEBandList']['LTEBand'][0]["Value"], 16) & (1 << (b-1))) == 0:
        log.error("The Modem does not support B%d" % b)
        sys.exit(-1)
    change_required = False
    mode = api.net_mode()
    if args.disable:
        if ((int(mode['NetworkMode']) != 0) or
           ((int(mode['LTEBand'], 16) & (1 << (b-1))) != 0)):
            # clear band
            band = int(mode['LTEBand'], 16) & (0xFFFFFFFFFF - (1 << (b-1)))
            change_required = True
        else:
            log.info("Already automatic mode without B%d" % b)
    else:
        if ((int(mode['NetworkMode']) != 0) or
           ((int(mode['LTEBand'], 16) & (1 << (b-1))) == 0)):
            # Set band
            band = int(mode['LTEBand'], 16) | (1 << (b-1))
            change_required = True
        else:
            log.info("Already automatic mode with B%d" % b)
    if change_required:
        # Automatic mode (2G/3G/4G)
        mode['NetworkMode'] = "00"
        # Band mask
        mode['LTEBand'] = "%X" % band
        api.net_mode(mode)
        log.info("New network configuration sent, waiting 5s")
        time.sleep(5)
    signal = api.device_signal()
    if signal["band"]:
        log.info("Current Band: B" + signal["band"])
        log.info("RSRQ: " + signal["rsrq"])
        log.info("RSRP: " + signal["rsrp"])
        log.info("RSSI: " + signal["rssi"])
        log.info("SINR: " + signal["sinr"])
    else:
        log.warn("The modem is not in 4G")
