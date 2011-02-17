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

    
def random_tweet(via, debug_handler=None, count=1):
    
    conf = DBYAML.load('oauth')
    if not conf: return

    format = DBYAML.load('format')
    if not format: format = '%s'
    
    consumer = dict(consumer_key    = conf.get('consumer_key'   ),
                    consumer_secret = conf.get('consumer_secret'))
    
    from_user, from_token = via

    # 自爆
    suicide = False
    
    suicide_rate = DBYAML.load('suicide_rate')
    if suicide_rate:
        if count >= len(suicide_rate):
            suicide_rate = suicide_rate[-1]
        else:
            suicide_rate = suicide_rate[count]
            
        dice = random.random()
        if dice <= suicide_rate:
            suicide = True
        logging.debug('dice=%5.3f, rate=%5.3f' % (dice, suicide_rate))
    logging.info('count = %s [%s]' % (count, suicide))
    
    
    if suicide:
        lst = [ from_token ]
    else:
        lst = OAuthAccessToken.get_random_access_token(15)
        if from_token in lst:
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
            
            handler = libs.auth.OAuthHandler(handler=self, conf=conf)
            handler.login()
            # redirect (not reached)
            
        elif action == 'callback':
            conf = DBYAML.load('oauth')
            if not conf: return
            
            now = datetime.datetime.now() + datetime.timedelta(hours=+9)
            logging.info('%s [%s]' % (action, now))
            
            handler = libs.auth.OAuthHandler(handler=self, conf=conf)
            items = handler.callback()
            if not items:
                logging.warning('callback error!')
                return self.redirect("/")
            
            name, access_token = items
            
            session_id = self.request.cookies.get('session_id')
            if session_id is None:
                session_id = str(random.getrandbits(64))
                expires = datetime.datetime.now() + datetime.timedelta(minutes=5)
                expires = expires.strftime('%a, %d %b %Y %H:%M:%S GMT')
                
                self.response.headers.add_header(  
                    'Set-Cookie', 'session_id=%s;expires=%s' % (session_id, expires))
                logging.info('SET: session_id: %s' % session_id)
                memcache.set(key=session_id, value=0, time=120)
            else:
                memcache.add(key=session_id, value=0, time=120)
            count = memcache.incr(session_id)
            if count is None:
                count = 1
                logging.warning('memcache replace')
                memcache.set(key=session_id, value=1, time=120)
            
            # random tweet
            result = random_tweet( via=(name, access_token), count=count )
            if result < 0: OAuthAccessTokenCount.add_count(result)
            
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



def main():
    application = webapp.WSGIApplication([
            ('^/(.*?)/?$'      , MainHandler ),
            ], debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
