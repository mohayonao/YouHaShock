#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import yaml
import urllib
import logging

# for OAuth
import time
import hmac
import random
import hashlib

from django.utils import simplejson
from google.appengine.api import urlfetch

# yaml for twitter api is the below format
# 'http://api.twitter.com/1':
#   'statuses':
#     - [ 'show'  , 'GET' , 'show'  , ''       ]
#     - [ 'update', 'POST', 'update'. 'status' ]
#   'account':
#     - [ 'verify_credentials', 'GET', 'verify_credentials.json', '' ]
#
# Twitter API Documentation:
#   http://apiwiki.twitter.com/Twitter-API-Documentation
#
def get_api_list(filename):
    result = []
    def makelist(d, prefix=''):
        for k, v in d.iteritems():
            prefix_parts = [ prefix, k ]
            if k == '': prefix_parts = prefix_parts[0]
            elif k[-1] != '/': prefix_parts.append('/')
            new_prefix = ''.join(prefix_parts)
            
            if isinstance(v, dict):
                makelist(v, new_prefix)
            elif isinstance(v, list):
                for name, http_method, url, require in v:
                    url = ''.join([new_prefix, url, '.json'])
                    result.append((name, http_method.upper(), url, require))
    if os.path.exists(filename):
        makelist(yaml.load(open(filename).read()))
    return result


def get_api_callee(method_p, name, url, require):

    def call_api(**argv):
        if require:
            require_set = set( x.strip() for x in require.split(',') )
            
            lack = list(require_set - set(argv.keys()))
            if lack:
                if len(lack) == 1:
                    params = lack[0]
                else:
                    params = '%s and %s' % (', '.join(lack[:-1]), lack[-1])
                error_message = '%s requires parameters %s' % (name, params)
                raise KeyError, error_message
        
        request_url = url % argv
        logging.debug('api: %s (%s)' % (name, request_url))
        return method_p(request_url, **argv)
    return call_api


class OAuth:
    def __init__(self, consumer, token):
        self.consumer_key    = consumer.get('consumer_key')
        self.consumer_secret = consumer.get('consumer_secret')
        self.token           = token.get('token')
        self.token_secret    = token.get('token_secret')


class TwitterAPI:
    def __init__(self, oauth):
        self.oauth = oauth
        self.impl_api = {}
        self.bind_api_methods()
    
    
    # bind methods for twitter api defined twitterapi.yaml
    def bind_api_methods(self):
        filepath = '%s/twitterapi.yaml' % os.path.dirname(__file__)
        apilist  = get_api_list(filepath)
        method_dict = dict( GET=self.GET, POST=self.POST, DELETE=self.DELETE)
        
        for name, http_method, url, require in apilist:
            if name in self.impl_api: continue
            
            method = method_dict.get(http_method)
            if method:
                setattr(self, name, get_api_callee(method, name, url, require))
                self.impl_api[name] = getattr(self, name)
    
    
    def call(self, api_name, **argv):
        if api_name in self.impl_api:
            return self.impl_api[api_name](**argv)
        else:
            raise UnboundLocalError, 'API is not implemented: "%s"' % api_name
    
    
    def GET(self, url, **extra_params):
        url = self.get_signed_url(url, self.oauth, 'GET', **extra_params);
        fetch_params = dict(url=url, method=urlfetch.GET)

        fetch_result = urlfetch.fetch(deadline=15, **fetch_params)
        if fetch_result.status_code == 200:
            return simplejson.loads(fetch_result.content)
        else:
            raise urlfetch.InvalidURLError
    
    
    def POST(self, url, **extra_params):
        payload = self.get_signed_body(url, self.oauth, 'POST', **extra_params)
        fetch_params = dict(url=url, method=urlfetch.POST, payload=payload)
        
        fetch_result = urlfetch.fetch(deadline=15, **fetch_params)
        if fetch_result.status_code == 200:
            return simplejson.loads(fetch_result.content)
        else:
            raise urlfetch.InvalidURLError
        
    
    def DELETE(self, url, **extra_params):
        extra_params['_method'] = 'DELETE'
        return self.POST(url, **extra_params)
    
    
    def get_signed_url(self, url, oauth, method, **extra_params):
        query_string = self.get_signed_body(url, oauth, method, **extra_params)
        return '%s?%s' % (url, query_string)
    
    
    def get_signed_body(self, url, oauth, method, **extra_params):
        
        def encode(text):
            return urllib.quote(str(text), '')
        
        kwargs = {
            'oauth_consumer_key': oauth.consumer_key,
            'oauth_signature_method': 'HMAC-SHA1',
            'oauth_version': '1.0',
            'oauth_timestamp': int(time.time()),
            'oauth_nonce': random.getrandbits(64),
            'oauth_token': oauth.token,
            }
        for k, v in extra_params.iteritems():
            if isinstance(v, unicode):
                extra_params[k] = v.encode('utf-8')
        kwargs.update(extra_params)
        
        kv = ['%s=%s' % (encode(k), encode(kwargs[k])) for k in sorted(kwargs)]
        q  = '&'.join(map(encode, [ method.upper(), url, '&'.join(kv) ]))
        
        service_key  = encode(oauth.consumer_secret)
        token_secret = encode(oauth.token_secret)
        oauth_key    = '%s&%s'% (service_key, token_secret)
        
        kwargs['oauth_signature'] = \
            hmac.new(oauth_key, q, hashlib.sha1).digest().encode('base64')[:-1]
        
        return urllib.urlencode(kwargs)



