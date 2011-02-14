#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


import os
import yaml
import random
import logging
import datetime

from google.appengine.dist import use_library
use_library('django', '1.2')

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api.labs import taskqueue

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template

from google.appengine.ext import db

import libs.auth
import libs.timeago

from libs.twitter import OAuth, TwitterAPI

from model import OAuthRequestToken, OAuthAccessToken
from model import OAuthAccessTokenCount
from model import YouHaShockHistory
from model import DBYAML



################################################################################
## misc
################################################################################
def random_description():
    lst = DBYAML.load('description')
    if lst: return random.choice(lst)
    

def random_word():
    lst = DBYAML.load('words')
    if lst: return random.choice(lst)
    
    
def tweet_user_link(name):
    name = name.encode('utf-8')
    return """<a href="http://twitter.com/%s" target="twitter">@%s</a>""" % (name, name)


def tweet_status_link(user, status_id, caption):
    user      = user.encode('utf-8')
    caption   = caption.encode('utf-8')
    return """<i>(<a href="http://twitter.com/%s/status/%s" target="twitter">%s</a>)</i>""" % \
        (user, status_id, caption)


def random_tweet(via, debug_handler=None, refrect_lv=0):
    
    conf = DBYAML.load('oauth')
    if not conf: return

    format = DBYAML.load('format')
    if not format: format = '%s'
    
    consumer = dict(consumer_key    = conf.get('consumer_key'   ),
                    consumer_secret = conf.get('consumer_secret'))
    
    from_user, from_token = via
    
    lst = OAuthAccessToken.get_random_access_token(10)
    if from_token not in lst:
        lst.append(from_token)
        
    for i in xrange(refrect_lv * 3):
        lst.append(from_token)

    refrect_count = lst.count(from_token)
    logging.info('refrect(%s): %5.3f' % (from_user, float(refrect_count) / len(lst)))
    
    random.shuffle(lst)
    
    result = 0
    for item in lst:
        word   = random_word()
        status = format % word
        
        token  = dict(token        = item.oauth_token,
                      token_secret = item.oauth_token_secret)
        oauth  = OAuth(consumer, token)
        
        api_result = None
        try:
            if debug_handler:
                api_result = TwitterAPI(oauth).verify()
            else:
                api_result = TwitterAPI(oauth).tweet(status=status)
                
        except urlfetch.DownloadError:
            logging.warning('tweet failed: timeout')
            
        except urlfetch.InvalidURLError:
            if debug_handler:
                debug_handler.response.out.write('tweet failed: invalid access_token %s<br/>' % item.oauth_token)
                
            else:
                logging.info('tweet failed: invalid access_token %s' % item.oauth_token)
                item.delete()
                result -= 1
            
        else:
            item.put() # update
            
            to_user = api_result.get('user'  , {}).get('screen_name')
            if not to_user: to_user = api_result.get('screen_name', u'unknown')
            if to_user:     to_user = to_user.encode('utf-8')
            
            if debug_handler:
                debug_handler.response.out.write('%s (posted by %s via %s)' % (status, to_user, from_user))
            else:
                status_id   = int(api_result.get('id', 0))
                params = dict( from_user = from_user, to_user   = to_user,
                               word      = word     , status_id = status_id )
                YouHaShockHistory.set_history(**params)
                
                logging.info('%s (posted by %s via %s)' % (status, to_user, from_user))
            return result
    else:
        logging.warning('tweet failed')
        return result



################################################################################
## handler
################################################################################
class MainHandler(webapp.RequestHandler):
    """YouはShock本体"""
    
    def get(self, action):
        
        if action == 'verify':
            conf = DBYAML.load('oauth')
            if not conf: return
            
            now = datetime.datetime.now() + datetime.timedelta(hours=+9)
            logging.info('%s [%s]' % (action, now))
            
            # memcache
            session_id = self.request.cookies.get('session_id')
            cacheitem  = None
            if session_id is not None:
                logging.debug('GET: session_id: %s' % session_id)
                cacheitem = memcache.get(session_id)
                logging.debug('memcache.get: session_id: %s; %s' % (session_id, cacheitem))
                
            if cacheitem is None:
                logging.info('new verify')
                handler = libs.auth.OAuthHandler(handler=self, conf=conf)
                handler.login()
                # redirect (not reached)
                
            else:
                logging.info('cached verify')
                name = cacheitem['name']
                key_name = '_%s' % cacheitem['oauth_token'][:15]
                ent = OAuthAccessToken(key_name=key_name)
                ent.oauth_token        = cacheitem['oauth_token']
                ent.oauth_token_secret = cacheitem['oauth_token_secret']
                cacheitem['count'] += 1
                
                memcache.set(session_id, cacheitem)
                
                # random tweet                
                refrect_lv = cacheitem.get('count', 0)
                result = random_tweet( via=(name, ent), refrect_lv=refrect_lv)
                if result < 0:
                    OAuthAccessTokenCount.add_count(result)
                    
                return self.redirect("/")
                # redirect (not reached)
            
            
        elif action == 'callback':
            conf = DBYAML.load('oauth')
            if not conf: return
            
            now = datetime.datetime.now() + datetime.timedelta(hours=+9)
            logging.info('%s [%s]' % (action, now))
            
            handler = libs.auth.OAuthHandler(handler=self, conf=conf)
            name, access_token = handler.callback()
            
            # memcache
            session_id = self.request.cookies.get('session_id')
            if session_id is None:
                session_id = str(random.getrandbits(64))
                expires = datetime.datetime.now() + datetime.timedelta(minutes=5)
                self.response.headers.add_header(  
                    'Set-Cookie', 'session_id=%s;expires=%s' % (session_id, expires))
                logging.debug('SET: session_id: %s' % session_id)
                
            cacheitem = dict(name=name,
                             oauth_token=access_token.oauth_token,
                             oauth_token_secret=access_token.oauth_token_secret,
                             count=0)
            memcache.add(session_id, cacheitem, time=300)
            logging.debug('memcache.add: session_id: %s; %s' % (session_id, cacheitem))
            
            # random tweet
            result = random_tweet( via=(name, access_token) )
            if result < 0:
                OAuthAccessTokenCount.add_count(result)
            
            return self.redirect("/")
            # redirect (not reached)
            
        else:
            template_value = {}
            description = random_description()
            if description: template_value['description'] = description
            
            ad = DBYAML.load('ad')
            if ad: template_value['ad'] = ad
            
            html = template.render('tmpl/index.html', template_value)
            self.response.out.write(html)



class APIHandler(webapp.RequestHandler):
    """API"""
    
    def get(self, action):
        if action == 'history':
            page = int(self.request.get('page', 0))
            history = []
            lst = YouHaShockHistory.get_histories(page)
            for item in lst:
                from_user = tweet_user_link(item.from_user)
                to_user   = tweet_user_link(item.to_user  )
                if isinstance(item.word, unicode):
                    word = item.word.encode('utf-8')
                else:
                    word = item.word
                link = tweet_status_link(item.to_user, item.status_id, libs.timeago.get_elapsed(item.created))
                format = '%s が %s に <span class="word">%s</span> といわせた %s'
                histroy_str = format % (from_user, to_user, word, link)
                history.append("'%s'" % histroy_str)
            self.response.out.write('[%s]' % ','.join(history))



class AdminHandler(webapp.RequestHandler):
    """管理者用ページ"""
    
    def get(self, action):

        action = action.split('/')
        action, args = action[0], action[1:]
        
        if action == 'edit':
            filelist = [ ent.key().name()[1:] for ent in DBYAML.all() ]
            html = template.render('tmpl/edit.html', { 'filelist': filelist })
            self.response.out.write(html)
            
        elif action == 'load' and args:
            key_name = '_%s' % args[0]
            ent = DBYAML.get_by_key_name(key_name)
            if ent: self.response.out.write(ent.yaml_text)

        elif action == 'dummy':
            for i in xrange(50):
                ent = OAuthRequestToken(key_name='_%s' % i)
                ent.oauth_token = str(random.getrandbits(64))
                ent.oauth_token_secret = str(random.getrandbits(64))
                ent.put()
                
        elif action == 'test':
            testuser = DBYAML.load('testuser')
            if testuser:
                ent = OAuthAccessToken()
                ent.oauth_token = testuser.get('oauth_token')
                ent.oauth_token_secret = testuser.get('oauth_token_secret')
                
                result = random_tweet( via=('testuser', ent), debug_handler=self )
                if result < 0:
                    OAuthAccessTokenCount.add_count(result)
                    
                    
    def post(self, action):
        if action == 'edit':
            params = dict(self.request.POST)
            cmd = params.get('submit')
            if cmd == 'SUBMIT':
                name = params.get('name')
                text = params.get('yaml-text')
                if name and text:
                    try: DBYAML.save(name, yaml.load(text))
                    except e: pass
            elif cmd == 'DELETE':
                key_name = '_%s' % params.get('name')
                ent = DBYAML.get_by_key_name(key_name)
                if ent: ent.delete()
        self.redirect('/admin/edit/')



class TaskHandler(webapp.RequestHandler):
    """定期処理"""
    
    def get(self, action):
        now = datetime.datetime.now() + datetime.timedelta(hours=+9)
        logging.info('cron: %s [%s]' % (action, now))
        
        if action == 'request':
            self.add_task_expired_request_tokens()
        elif action == 'access':
            self.add_task_verify_expired_access_tokens()
        elif action == 'recount':
            count = OAuthAccessToken.all().count()
            logging.info('OAuthAccessToken count=%s' % count)
            
            
            
            
    def post(self, action):
        if action == 'request':
            key_name = self.request.get('key_name')
            ent = OAuthRequestToken.get_by_key_name(key_name)
            if ent: ent.delete()
            
        elif action == 'access':
            key_name = self.request.get('key_name')
            result = self.verify_oauth_token(key_name)
            if not result: self.error(504)
            
            
            
    def add_task_expired_request_tokens(self):
        expired = datetime.datetime.now() + datetime.timedelta(minutes=10)
        expired_tokens = OAuthRequestToken.all().filter('created <', expired)

        if expired_tokens:
            for i, token in enumerate(expired_tokens[:20]):
                key_name = token.key().name()
                taskqueue.add(url='/task/request', params=dict(key_name=key_name), countdown=i/3)
        else:
            logging.info('expired request tokens: 0')
            
            
            
    def add_task_verify_expired_access_tokens(self):
        conf = DBYAML.load('oauth')
        if not conf: return
        
        expired = datetime.datetime.now() - datetime.timedelta(hours=2)
        expired_tokens = OAuthAccessToken.all().filter('modified <', expired)

        if expired_tokens:
            for i, token in enumerate(expired_tokens[:20]):
                key_name = token.key().name()
                taskqueue.add(url='/task/access', params=dict(key_name=key_name), countdown=i)
        else:
            logging.info('expired access tokens: 0')
            
            
            
    def verify_oauth_token(self, key_name):
        ent = OAuthAccessToken.get_by_key_name(key_name)
        if not ent: return
        token  = dict(token        = ent.oauth_token,
                      token_secret = ent.oauth_token_secret)
        
        conf = DBYAML.load('oauth')
        consumer = dict(consumer_key    = conf.get('consumer_key'   ),
                        consumer_secret = conf.get('consumer_secret'))
        
        oauth = OAuth(consumer, token)
        try:
            TwitterAPI(oauth).verify()
            
        except urlfetch.DownloadError:
            logging.warning("verify timeout: %s" % ent.oauth_token)
            return False
            
        except urlfetch.InvalidURLError:
            logging.info("delete access token: %s" % ent.oauth_token)
            ent.delete()
            OAuthAccessTokenCount.add_count(-1)
            return True
            
        else:
            logging.info("verify access token: %s" % ent.oauth_token)
            ent.put() # update
            return True



def main():
    application = webapp.WSGIApplication([
            ('^/api/(.*?)/?$'  , APIHandler  ),
            ('^/admin/(.*?)/?$', AdminHandler),
            ('^/cron/(.*?)/?$' , TaskHandler),
            ('^/task/(.*?)/?$' , TaskHandler),
            ('^/(.*?)/?$'      , MainHandler ),
            ], debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
