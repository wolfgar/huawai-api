#!/usr/bin/env python2
#
# coding: utf-8
#

import requests
import xmltodict
import uuid
import hashlib
import hmac
import logging
from binascii import hexlify
from collections import OrderedDict
from datetime import datetime


class HuaweiAPIException(Exception):
    def __init__(self, value):
        self.value = value

    def __str__(self):
        return repr(self.value)


class HuaweiAPI:
    HOME_URL = "http://{host}/html/home.html"
    API_URL = "http://{host}/api/"

    def __init__(self, passwd, host="192.168.8.1", user="admin", logfile=None):
        if logfile:
            logging.basicConfig(filename=logfile)
        stderrLogger = logging.StreamHandler()
        stderrLogger.setFormatter(logging.Formatter(logging.BASIC_FORMAT))
        logging.getLogger().addHandler(stderrLogger)
        self.log = logging.getLogger("huawei-api")
        self.api_url = self.API_URL.format(host=host)
        self.session = requests.Session()
        self.log.debug("Connect to {host}".format(host=host))
        try:
            self.session.get(self.HOME_URL.format(host=host),
                             timeout=(5.0, 5.0))
        except Exception as e:
            raise HuaweiAPIException("Connection failed: " + str(e))
        dev_info = self.device_info()
        if dev_info:
            self.log.info("Detected Device: " + dev_info['devicename'])
        self.log.debug("Authenticate for user " + user)
        self.__login(user, passwd)

    def __get_client_proof(self, clientnonce, servernonce,
                           password, salt, iterations):
        msg = "%s,%s,%s" % (clientnonce, servernonce, servernonce)
        salted_pass = hashlib.pbkdf2_hmac('sha256', password,
                                          bytearray.fromhex(salt), iterations)
        client_key = hmac.new(b'Client Key', msg=salted_pass,
                              digestmod=hashlib.sha256)
        stored_key = hashlib.sha256()
        stored_key.update(client_key.digest())
        signature = hmac.new(msg.encode('utf_8'),
                             msg=stored_key.digest(), digestmod=hashlib.sha256)
        client_key_digest = client_key.digest()
        signature_digest = signature.digest()
        client_proof = bytearray()
        i = 0
        while i < client_key.digest_size:
            val = ord(client_key_digest[i]) ^ ord(signature_digest[i])
            client_proof.append(val)
            i = i + 1
        return hexlify(client_proof)

    def __login(self, user, password):
        d = OrderedDict()
        d['username'] = user
        client_nonce = uuid.uuid4().hex + uuid.uuid4().hex
        d['firstnonce'] = client_nonce
        d['mode'] = 1
        data_login = self.__api_post('user/challenge_login', d)
        d = OrderedDict()
        proof = self.__get_client_proof(client_nonce,
                                        data_login['servernonce'],
                                        password,
                                        data_login['salt'],
                                        int(data_login['iterations']))
        d['clientproof'] = proof
        d['finalnonce'] = data_login['servernonce']
        self.__api_post('user/authentication_login', d)
        if self.__api_request('user/state-login'):
            return True
        return False

    def __get_token(self, session=True):
        api_method_url = 'webserver/SesTokInfo'
        if session:
            r = self.session.get(url=self.api_url + api_method_url,
                                 allow_redirects=False, timeout=(1.5, 1.5))
        else:
            r = requests.get(url=self.api_url + api_method_url,
                             allow_redirects=False, timeout=(1.5, 1.5))
        if r.status_code != 200:
            raise HuaweiAPIException("Error getting token .HTTP error: %d" %
                                     r.status_code)
        return xmltodict.parse(r.text)['response']['TokInfo']

    def __api_request(self, api_method_url, session=True):
        headers = {'__RequestVerificationToken': self.__get_token(session)}
        try:
            r = self.session.get(url=self.api_url + api_method_url,
                                 headers=headers,
                                 allow_redirects=False, timeout=(1.5, 1.5))
        except requests.exceptions.RequestException as e:
            raise HuaweiAPIException("Request %s failed: %s" %
                                     (api_method_url, str(e)))
        if r.status_code != 200:
            raise HuaweiAPIException("Request returned HTTP error %d" %
                                     r.status_code)
        self.log.debug("Request: " + api_method_url +
                       "\nResponse:\n" + r.content)
        resp = xmltodict.parse(r.text).get('error', None)
        if resp is not None:
            error_code = resp['code']
            raise HuaweiAPIException("Request returned error " + error_code)
        resp = xmltodict.parse(r.text).get('response', None)
        if resp is None:
            raise HuaweiAPIException("Request returned empty response")
        else:
            return resp

    def __api_post(self, api_method_url, data, session=True):
        headers = {'__RequestVerificationToken': self.__get_token(session)}
        request = {}
        request['request'] = data
        try:
            r = self.session.post(url=self.api_url + api_method_url,
                                  data=xmltodict.unparse(request, pretty=True),
                                  headers=headers, timeout=(1.5, 1.5))
        except requests.exceptions.RequestException as e:
            raise HuaweiAPIException("Request %s failed: %s" %
                                     (api_method_url, str(e)))
        if r.status_code != 200:
            raise HuaweiAPIException("Request returned HTTP error %d" %
                                     r.status_code)
        self.log.debug("Request: " + api_method_url +
                       "\nResponse:\n" + r.content)
        resp = xmltodict.parse(r.text).get('error', None)
        if resp is not None:
            error_code = resp['code']
            raise HuaweiAPIException("Request returned error " + error_code)
        resp = xmltodict.parse(r.text).get('response', None)
        if resp is None:
            raise HuaweiAPIException("Request returned empty response")
        else:
            return resp

    def send_sms(self, number, text):
        d = OrderedDict()
        d['Index'] = -1
        d['Phones'] = {'Phone': number}
        d['Sca'] = ''
        d['Content'] = text
        d['Length'] = len(text)
        d['Reserved'] = 1
        d['Date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.__api_post('sms/send-sms', d)

    def device_info(self):
        return self.__api_request('device/basic_information', session=False)

    def state_login(self):
        return self.__api_request('user/state-login')

    def check_notifications(self):
        return self.__api_request('monitoring/check-notifications')

    def device_signal(self):
        return self.__api_request('device/signal')

    def net_mode(self, params=None):
        if params is None:
            return self.__api_request('net/net-mode')
        else:
            return self.__api_post('net/net-mode', params)

    def sms_list(self):
        d = OrderedDict()
        d['PageIndex'] = 1
        d['ReadCount'] = 20
        d['BoxType'] = 1
        d['SortType'] = 0
        d['Ascending'] = 0
        d['UnreadPreferred'] = 0
        return self.__api_post('sms/sms-list', d)

    def sms_count(self):
        return self.__api_request('sms/sms-count')

    def sms_delete(self, index):
        d = OrderedDict()
        d['Index'] = index
        return self.__api_post('sms/delete-sms', d)

    def net_mode_list(self, params=None):
        if params is None:
            return self.__api_request('net/net-mode-list')
        else:
            return self.__api_post('net/net-mode-list', params)
