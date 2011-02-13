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

from google.appengine.api import urlfetch
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


def random_tweet(via, debug_handler=None):
    
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
        now = datetime.datetime.now() + datetime.timedelta(hours=+9)
        logging.info('%s [%s]' % (action, now))
        
        template_value = {}
        description = random_description()
        if description: template_value['description'] = description
        
        if action == 'verify':
            conf = DBYAML.load('oauth')
            if not conf: return
            handler = libs.auth.OAuthHandler(handler=self, conf=conf)
            handler.login()
            # redirect (not reached)
            
        elif action == 'callback':
            conf = DBYAML.load('oauth')
            if not conf: return
            handler = libs.auth.OAuthHandler(handler=self, conf=conf)
            name, access_token = handler.callback()
            
            result = random_tweet( via=(name, access_token) )
            if result < 0:
                OAuthAccessTokenCount.add_count(result)
                
            return self.redirect("/")
            # redirect (not reached)
            
        else:
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



class CronHandler(webapp.RequestHandler):
    """定期処理"""
            
    def get(self, action):
        now = datetime.datetime.now() + datetime.timedelta(hours=+9)
        logging.info('cron: %s [%s]' % (action, now))
        
        if action == 'request':
            self.delete_expired_request_tokens()
        else:
            self.delete_expired_access_tokens()

    
    def delete_expired_request_tokens(self):
        """残ってしまったOauthのRequestTokenを削除する"""
        expired = datetime.datetime.now() - datetime.timedelta(hours=2)
        expired_tokens = OAuthRequestToken.all().filter('created <', expired)
        
        count = 0
        for token in expired_tokens[:10]:
            token.delete()
            count += 1
        logging.info('delete expired tokens: %d' % count)
        if count:
            self.redirect(self.request.url)
        else:
            logging.info("delete request token: DONE")
            
            
            
    def delete_expired_access_tokens(self):
        """認証解除されたOauthのAccessTokenを削除する"""
        
        conf = DBYAML.load('oauth')
        if not conf: return
        
        consumer = dict(consumer_key    = conf.get('consumer_key'   ),
                        consumer_secret = conf.get('consumer_secret'))
        
        expired = datetime.datetime.now() - datetime.timedelta(hours=6)
        expired_token = OAuthAccessToken.all().filter('modified <', expired).get()
        if not expired_token:
            logging.info("verify access token: DONE")
            return
        
        token  = dict(token        = expired_token.oauth_token,
                      token_secret = expired_token.oauth_token_secret)
        oauth = OAuth(consumer, token)
        try:
            TwitterAPI(oauth).verify()
            
        except urlfetch.DownloadError:
            logging.warning("verify timeout: %s" % expired_token.oauth_token)
            
        except urlfetch.InvalidURLError:
            logging.info("delete access token: %s" % expired_token.oauth_token)
            expired_token.delete()
            OAuthAccessTokenCount.add_count(-1)
        else:
            logging.info("verify access token: %s" % expired_token.oauth_token)
            expired_token.put() # update
            
        self.redirect(self.request.url)



def main():
    application = webapp.WSGIApplication([
            ('^/api/(.*?)/?$'  , APIHandler  ),
            ('^/admin/(.*?)/?$', AdminHandler),
            ('^/cron/(.*?)/?$' , CronHandler),
            ('^/(.*?)/?$'      , MainHandler ),
            ], debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
