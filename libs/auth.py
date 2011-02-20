#!/usr/bin/env python
# -*- coding: utf-8 -*-

import time
import hmac
import random
import hashlib
import urllib
import logging

from google.appengine.ext import db
from google.appengine.api import urlfetch

from model import OAuthRequestToken, OAuthAccessToken


################################################################################
# misc
################################################################################
def encode(text):
    return urllib.quote(str(text), '')


################################################################################
# OAuthClient
################################################################################
class OAuthClient:
    def __init__(self, conf):
        self._bind_attribute(conf)
        
    def _bind_attribute(self, conf):
        if not isinstance(conf, dict): return
        for k, v in conf.iteritems():
            setattr(self, k, v)
    
    def get_request_url(self):
        request_url = self.get_data_from_signed_url(self.request_token_url)
        request_token = OAuthRequestToken.set_request_token(request_url)
        oauth_callback = { 'oauth_callback': self.oauth_callback }
        return self.get_signed_url( \
            self.user_auth_url, request_token, **oauth_callback)
    
    def get_data_from_signed_url(self, url, \
                                     token=None, method='GET', **extra_params):
        signed_url = self.get_signed_url(url, token, method, **extra_params)
        return urlfetch.fetch(signed_url).content
    
    def get_signed_url(self, url, token=None, method='GET', **extra_params):
        signed_body = self.get_signed_body(url, token, method, **extra_params)
        return '%s?%s' % (url, signed_body)
    
    def get_signed_body(self, url, token=None, method='GET', **extra_params):
        kwargs = { 'oauth_consumer_key': self.consumer_key,
                   'oauth_signature_method': 'HMAC-SHA1',
                   'oauth_version': '1.0',
                   'oauth_timestamp': int(time.time()),
                   'oauth_nonce': random.getrandbits(64), }
        kwargs.update(extra_params)
        
        key = service_key = '%s&' % encode(self.consumer_secret)
        
        if token is not None:
            kwargs['oauth_token'] = token.oauth_token
            key = '%s%s' % (service_key, encode(token.oauth_token_secret))
        
        q = '&'.join(
            '%s=%s' % (encode(k), encode(kwargs[k])) for k in sorted(kwargs) )
        
        query = '&'.join(
            map(encode, [ method.upper(), url, q ]) )
        
        kwargs['oauth_signature'] = \
            hmac.new(key, query, hashlib.sha1).digest().encode('base64')[:-1]
        
        return urllib.urlencode(kwargs)
    
    
        
################################################################################
# OAuthHandler
################################################################################
class OAuthHandler:
    __public__ = ('callback', 'login')

    def __init__(self, handler, conf):
        self.handler = handler
        self.client  = OAuthClient(conf)
        
    def login(self):
        url = self.client.get_request_url()
        self.handler.redirect(url)
        
    def callback(self):
        oauth_token = self.handler.request.get('oauth_token')
        if not oauth_token: self.login()
        
        # Request Token
        request_token = OAuthRequestToken.get_request_token(oauth_token)
        if not request_token:
            logging.warning('callback: None Request Token')
            return
        
        access_url = self.client. \
            get_data_from_signed_url(self.client.access_token_url, request_token)
        # request_token.delete()
        
        # Access Token
        try:
            params = dict(token.split('=') for token in access_url.split('&'))
        except:
            logging.warning('callback: Invalid URL=%s' % access_url)
            return
        
        name = params.get('screen_name')
        if not name:
            logging.warning('callback: screen_name is None')
            return
        
        access_token = OAuthAccessToken.set_access_token(access_url)
        return name, access_token
