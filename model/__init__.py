#!/usr/bin/env python
# -*- coding: utf-8 -*-

import yaml
import random
import logging

from google.appengine.ext import db

################################################################################
# misc
################################################################################
def url2dict(url):
    return dict(token.split('=') for token in url.split('&'))


################################################################################
# model
################################################################################
class OAuthRequestToken(db.Model):
    """OAuth Request Token."""
    oauth_token        = db.StringProperty()
    oauth_token_secret = db.StringProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    
    @classmethod
    def request_token_key_name(cls, obj):
        if isinstance(obj, dict): obj = obj.get('oauth_token')
        return '_%s' % obj[:7]
    
    @classmethod
    def get_request_token(cls, name):
        key_name = cls.request_token_key_name(name)
        return OAuthRequestToken.get_by_key_name(key_name)
    
    @classmethod
    def set_request_token(cls, url):
        params = url2dict(url)
        key_name = cls.request_token_key_name(params)
        token  = OAuthRequestToken(key_name=key_name, **params)
        token.put()
        return token


class OAuthAccessToken(db.Model):
    """OAuth Access Token."""
    oauth_token        = db.StringProperty()
    oauth_token_secret = db.StringProperty()
    randint  = db.IntegerProperty(default=0)
    created  = db.DateTimeProperty(auto_now_add=True)
    modified = db.DateTimeProperty(auto_now=True)
    
    
    @classmethod
    def get_access_token(cls, params=None, url=None):
        if params is None:
            params = url2dict(url)
        key_name = '_%s' % params['oauth_token'][:15]
        token  = OAuthAccessToken.get_or_insert(key_name)
        token.oauth_token        = params['oauth_token']
        token.oauth_token_secret = params['oauth_token_secret']
        return token
    
    
    @classmethod
    def get_random_access_token(cls, n=20):
        
        for i in xrange(3):
            a = random.randint(0, 900)
            b = a + 100
            
            lst = OAuthAccessToken.gql("WHERE randint >= :1 AND randint < :2", a, b).fetch(n)
            if lst: break
            
        return lst



class YouHaShockHistory(db.Model):
    from_user = db.StringProperty()
    to_user   = db.StringProperty()
    word      = db.StringProperty()
    status_id = db.IntegerProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    

class UserStatus(db.Model):
    profile_image_url = db.StringProperty()
    profile_image_updated = db.DateTimeProperty()
    call_count   = db.IntegerProperty(default=0)
    callee_count = db.IntegerProperty(default=0)
    graph    = db.TextProperty()
    modified = db.DateTimeProperty(auto_now=True)
    


class DBYAML(db.Model):
    yaml_text = db.TextProperty()
    created   = db.DateTimeProperty(auto_now_add=True)
    
    @classmethod
    def load(cls, name):
        key_name = '_%s' % name
        entity = DBYAML.get_by_key_name(key_name)
        result = None
        if entity:
            try:
                result = yaml.load(entity.yaml_text)
            except yaml.parser.ParserError:
                logging.warning('YAML ParseError: %s.yaml' % name)
        else:
            logging.warning('%s is not in DBYAML' % name)
        return result
    
    
    @classmethod
    def save(cls, name, params):
        key_name = '_%s' % name
        yaml_text = yaml.safe_dump(params, encoding='utf8',
                     allow_unicode=True, default_flow_style=False)
        yaml_text = yaml_text.decode('utf-8')
        entity = DBYAML.get_by_key_name(key_name)
        if entity:
            entity.yaml_text = yaml_text
        else:
            entity = DBYAML(key_name=key_name, yaml_text=yaml_text)
        entity.put()
        
