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
        token = OAuthAccessToken.get_by_key_name(key_name)
        if not token:
            token = OAuthAccessToken(key_name=key_name)
            token.oauth_token        = params['oauth_token']
            token.oauth_token_secret = params['oauth_token_secret']
            logging.debug('new OAuthAccessToken')
        return token
    
    @classmethod
    def get_random_access_token(cls, n=20):
        
        for i in xrange(3):
            a = random.randint(0, 995)
            b = a + 20
            
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


class Ranking(db.Model):
    data = db.TextProperty()
    
    
class DBYAML(db.Model):
    yaml_text = db.TextProperty()
    created   = db.DateTimeProperty(auto_now_add=True)
    
    _settings  = None

    @classmethod
    def init(cls):
        entity = DBYAML.get_by_key_name('settings')
        if entity:
            try:
                cls._settings = yaml.load(entity.yaml_text)
            except yaml.parser.ParserError:
                cls._settings = {}
                logging.error('YAML ParseError!')
        else:
            cls._settings = {}
            logging.error('setting YAML is not existed!')
    
    
    @classmethod
    def load(cls, name):
        if cls._settings is None:
            cls.init()
        
        if isinstance(cls._settings, dict):
            return cls._settings.get(name)
        
        
    @classmethod
    def save(cls, name, text):
        if cls._settings is None:
            cls.init()
        
        if not isinstance(cls._settings, dict):
            return
        
        try:
            params = yaml.load(text)
        except:
            logging.error('YAML parse error! %s' % text)
            return
        
        cls._settings[name] = params
        
        entity = DBYAML.get_or_insert('settings')
        yaml_text = yaml.safe_dump(cls._settings,
                                   encoding='utf8',
                                   allow_unicode=True,
                                   default_flow_style=False)
        yaml_text = yaml_text.decode('utf-8')
        
        entity.yaml_text = yaml_text
        entity.put()
        
        
    @classmethod
    def delete(cls, name):
        if cls._settings is None:
            cls.init()
            
        if not isinstance(cls._settings, dict):
            return
        
        if name not in cls._settings:
            return
        
        del cls._settings[name]
            
        entity = DBYAML.get_or_insert('settings')
        yaml_text = yaml.safe_dump(cls._settings,
                                   encoding='utf8',
                                   allow_unicode=True,
                                   default_flow_style=False)
        yaml_text = yaml_text.decode('utf-8')
        
        entity.yaml_text = yaml_text
        entity.put()
    
    
    @classmethod
    def catalog(cls):
        settings = DBYAML.get_by_key_name('settings')
        if settings:
            filelist = yaml.load(settings.yaml_text).keys()
            filelist.sort()
            return filelist
        else:
            return []
        
        
    @classmethod
    def loadtext(cls, name):
        if cls._settings is None:
            cls.init()
        
        data = cls._settings.get(name)
        if data:
            text = yaml.safe_dump(data, encoding='utf8',
                                  allow_unicode=True,
                                  default_flow_style=False)
            return text
        return ''
