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
from model.model  import OAuthRequestToken, OAuthAccessToken
from model.model  import OAuthAccessTokenCount
from model.model  import YouHaShockHistory
from model.model  import DBYAML



################################################################################
## misc
################################################################################
def random_lyric():
    lst = DBYAML.load('lyrics')
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


def random_tweet(me):
    
    from_user = me.key().name()
    from_user = from_user[1:]
    
    conf = DBYAML.load('oauth')
    if not conf: return
    logging.info('using: %s' % from_user)
    
    consumer = dict(consumer_key    = conf.get('consumer_key'   ),
                    consumer_secret = conf.get('consumer_secret'))
    
    lst = OAuthAccessToken.get_random_access_token(10)
    if me not in lst:
        lst.append(me)
    random.shuffle(lst)
    
    logging.info('access token count: %d' % len(lst))
    
    result = 0
    for item in lst:
        screen_name = item.key().name()
        screen_name = screen_name[1:]
        
        word   = random_word()
        status = '%s #youhashock' % word
        
        token  = dict(token        = item.oauth_token,
                      token_secret = item.oauth_token_secret)
        oauth  = OAuth(consumer, token)
        
        api_result = None
        try:
            api_result = TwitterAPI(oauth).tweet(status=status)
            
        except urlfetch.DownloadError:
            logging.warning('tweet failed: timeout')
            
        except urlfetch.InvalidURLError:
            logging.info('tweet failed: invalid user %s' % screen_name)
            item.delete()
            result -= 1
            
        else:
            status_id   = int(api_result.get('id', 0))
            screen_name = api_result.get('user'  , {}).get('screen_name')
            if not screen_name: screen_name = api_result.get('screen_name', u'unknown')
            if screen_name:     screen_name = screen_name.encode('utf-8')
            
            params = dict(
                from_user = from_user, to_user   = screen_name,
                word      = word     , status_id = status_id
                )
            YouHaShockHistory.set_history(**params)
            
            logging.info('%s (posted by %s)' % (status, screen_name))
            return result
    else:
        logging.warning('tweet failed')
        return result



def check(self):
    
    conf = DBYAML.load('oauth')
    if not conf: return
    
    consumer = dict(consumer_key    = conf.get('consumer_key'   ),
                    consumer_secret = conf.get('consumer_secret'))
    
    lst = OAuthAccessToken.get_random_access_token(10)
    
    result = 0
    for item in lst:
        screen_name = item.key().name()
        screen_name = screen_name[1:]
        
        self.response.out.write('CHECK: %s  ' % screen_name)
        
        token  = dict(token        = item.oauth_token,
                      token_secret = item.oauth_token_secret)
        oauth  = OAuth(consumer, token)
        
        api_result = None
        try:
            api_result = TwitterAPI(oauth).verify()
            
        except urlfetch.DownloadError:
            self.response.out.write('--> timeout<br>')
            
        except urlfetch.InvalidURLError:
            self.response.out.write('--> invalid<br>')
            item.delete()
            
        else:
            self.response.out.write('--> enabled<br>')
        self.response.out.write('<hr>')

            
        
    
    

################################################################################
## handler
################################################################################
class APIHandler(webapp.RequestHandler):
    
    def get(self, action):
        if action == 'history':
            data = DBYAML.load('history')
            if not data: 
                self.response.out.write('[]')
                return
            format = data.encode('utf-8')
            
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
                histroy_str = format % (from_user, to_user, word, link)
                
                history.append("'%s'" % histroy_str)
            self.response.out.write('[%s]' % ','.join(history))




class AdminHandler(webapp.RequestHandler):
    def get(self, action):
        if action == 'edit':
            html = template.render('tmpl/edit.html', {})
            self.response.out.write(html)
        elif action == 'check':
            check(self)
            
            
    def post(self, action):
        if action == 'edit':
            params = dict(self.request.POST)
            
            name = params.get('name')
            text = params.get('text')
            
            if name and text:
                DBYAML.save(name, yaml.load(text));
                self.response.out.write('do %s : OK' % action)
            





class MainHandler(webapp.RequestHandler):
    
    def get(self, action):
        template_value = { 'lyric': random_lyric() }
        
        if action == 'verify':
            logging.info('call verify')
            conf = DBYAML.load('oauth')
            if not conf: return
            handler = libs.auth.OAuthHandler(handler=self, conf=conf)
            handler.login()
            # redirect (not reached)
            
        elif action == 'callback':
            logging.info('call callback')
            conf = DBYAML.load('oauth')
            if not conf: return
            handler = libs.auth.OAuthHandler(handler=self, conf=conf)
            access_token = handler.callback()
            
            result = random_tweet(me=access_token)
            if result < 0:
                OAuthAccessTokenCount.add_count(result)
                
            return self.redirect("/")
            # redirect (not reached)
            
        else:
            html = template.render('tmpl/index.html', template_value)
            self.response.out.write(html)




def main():
    random.seed(datetime.datetime.now().microsecond)
    
    application = webapp.WSGIApplication([
            ('^/api/(.*?)/?$'  , APIHandler  ),
            ('^/admin/(.*?)/?$', AdminHandler),
            ('^/(.*?)/?$'      , MainHandler ),
            ], debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
