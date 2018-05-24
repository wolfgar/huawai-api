#!/usr/bin/env python2
#
# coding: utf-8
#

from commonargs import get_huawei_from_args
import logging
import argparse
import time


class HandleSMS:
    def __init__(self, api, period):
        self._api = api
        self._period = period
        self._log = logging.getLogger("sms")

    def _process_sms(self, msg):
        if int(msg['Smstat']) == 1:
            flag = "Read: "
        else:
            flag = "Unread: "
        self._log.info("{state} From {number} ({date}) (idx {idx})".format(
                       state=flag, number=msg['Phone'], date=msg['Date'],
                       idx=msg['Index']))
        self._log.info("\t" + msg['Content'])
        self._api.sms_delete(msg['Index'])

    def run(self):
        while True:
            sms = self._api.sms_list()
            count = int(sms['Count'])
            self._log.debug("SMS available: {}".format(count))
            if count > 0:
                # if count > 1
                #     sms["Messages"]["Message"] is a list of OrderedDict
                # if count == 1
                #     it is directly an OrderedDict
                if count > 1:
                    for msg in sms["Messages"]["Message"]:
                        self._process_sms(msg)
                else:
                    self._process_sms(sms["Messages"]["Message"])
            time.sleep(self._period)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Read SMS demo")
    parser.add_argument("--period",
                        help="Poll period",
                        type=int,
                        default=5,
                        required=False)
    api, args = get_huawei_from_args(parser)
    h = HandleSMS(api, args.period)
    h.run()
