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



class OAuthAccessTokenCount(db.Model):
    count   = db.IntegerProperty()
    updated = db.DateTimeProperty(auto_now=True)
    
    @classmethod
    def get_count(cls):
        entity = OAuthAccessTokenCount.get_by_key_name('_')
        if entity:
            return entity.count
        else:
            return 0

    @classmethod
    def add_count(cls, val):
        entity = OAuthAccessTokenCount.get_by_key_name('_')
        if entity:
            entity.count += val
        else:
            if val < 0: val = 0
            entity = OAuthAccessTokenCount(key_name='_', count=val)
        entity.put()            
    


class OAuthAccessToken(db.Model):
    """OAuth Access Token."""
    oauth_token        = db.StringProperty()
    oauth_token_secret = db.StringProperty()
    created  = db.DateTimeProperty(auto_now_add=True)
    modified = db.DateTimeProperty(auto_now=True)
    
    @classmethod
    def get_access_token(cls, name):
        key_name = '_%s' % name
        return OAuthAccessToken.get_by_key_name(key_name)
    
    
    @classmethod
    def set_access_token(cls, url):
        params = url2dict(url)
        key_name = '_%s' % params['oauth_token'][:15]
        token  = OAuthAccessToken.get_by_key_name(key_name)
        if token:
            token.oauth_token        = params['oauth_token']
            token.oauth_token_secret = params['oauth_token_secret']
        else:
            token = OAuthAccessToken(key_name=key_name, **params)
            OAuthAccessTokenCount.add_count(1)
        token.put()
        return token
    
    
    @classmethod
    def get_random_access_token(cls, n=20):
        count = OAuthAccessTokenCount.get_count()
        m = count - n
        if m < 0:
            offset = 0
        else:
            offset = random.randint(0, m)
            
        gql = db.GqlQuery('SELECT * FROM OAuthAccessToken')
        lst = gql.fetch(20, offset)
        random.shuffle(lst)
        return lst



class YouHaShockHistory(db.Model):
    from_user = db.StringProperty()
    to_user   = db.StringProperty()
    word      = db.StringProperty()
    status_id = db.IntegerProperty()
    created = db.DateTimeProperty(auto_now_add=True)
    
    @classmethod
    def set_history(cls, **params):
        YouHaShockHistory(**params).put()
        
        
    @classmethod
    def get_histories(cls, page):
        gql = db.GqlQuery('SELECT * FROM YouHaShockHistory ORDER BY created DESC')
        lst = gql.fetch(20, page * 20)
        return lst



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
        
