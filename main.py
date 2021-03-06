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

# from google.appengine.dist import use_library
# use_library('django', '1.2')

from google.appengine.api import memcache
from google.appengine.api import urlfetch
from google.appengine.api.labs import taskqueue

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template

from google.appengine.ext import db

import libs.auth
import libs.cpu

from libs.twitter import OAuth, TwitterAPI


from model import OAuthRequestToken, OAuthAccessToken
from model import YouHaShockHistory
from model import DBYAML



################################################################################
## misc
################################################################################
def random_tweet(via, count=1):
    
    conf = DBYAML.load('oauth')
    if not conf: return
    
    words = DBYAML.load('words')
    if not words: return
    
    format = DBYAML.load('format')
    if not format: format = '%s'
    
    consumer = dict(consumer_key    = conf.get('consumer_key'   ),
                    consumer_secret = conf.get('consumer_secret'))
    
    from_token = via
    from_user  = from_token._name
    
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
    
    
    chk = libs.cpu.CPUChecker("random_tweet")
    chk.kokokara()
    if suicide:
        lst = [ from_token ]
    else:
        lst = OAuthAccessToken.get_random_access_token(5)
        random.shuffle(lst)
        lst.append(from_token)
    chk.kokomade("OAuthAccessToken.get_random_access_token")
    
    word   = random.choice(words)
    status = format % word
    
    for i, item in enumerate(lst):
        logging.debug('random_tweet: try=%d' % (i+1))
        
        token  = dict(token        = item.oauth_token,
                      token_secret = item.oauth_token_secret)
        api = TwitterAPI(OAuth(consumer, token))
        
        chk.kokokara()        
        api_result = None
        try:
            # api_result = api.verify()
            api_result = api.tweet(status=status)
            
        except urlfetch.DownloadError:
            api_result = None
            logging.warning('tweet failed: timeout')
            
        except urlfetch.InvalidURLError:
            api_result = None
            item.delete()
            logging.warning('tweet failed: invalid access_token %s' % item.oauth_token)
            
        chk.kokomade("api_result = api.tweet(status=status)")
        if not api_result: continue
        
        
        chk.kokokara()
        to_user = api_result.get('user', {}).get('screen_name').encode('utf-8')
        status_id = int(api_result.get('id', 0))
        if status_id:
            YouHaShockHistory( from_user = from_user, to_user   = to_user,
                               word      = word     , status_id = status_id ).put()
            logging.info('%s (posted by %s via %s)' % (status, to_user, from_user))
        chk.kokomade("YouHaShockHistory")
        
        
        chk.kokokara()
        expired = datetime.datetime.now() - datetime.timedelta(hours=2)
        if from_token.is_saved():
            # 既存ユーザー
            if from_token.modified < expired:
                from_token.randint = random.randint(0, 1000)
                from_token.put()
        else:
            # 新規ユーザー
            from_token.randint = random.randint(0, 1000)
            from_token.put()
            if item == from_token:
                # 新規ユーザーが自爆したときAPIの結果からアイコン画像のURLをメモしておく
                profile_image_url = api_result.get('user', {}).get('profile_image_url')
                key_name = 'at_%s' % to_user
                memcache.add(key=key_name, value=profile_image_url)
                
        if item != from_token:
            if item.modified < expired:
                item.randint = random.randint(0, 1000)
                item.put()
        chk.kokomade("TokenUpdate")
        
        return True # break
    return False



################################################################################
## handler
################################################################################
class MainHandler(webapp.RequestHandler):
    """YouはShock本体"""
    
    def default_page(self, errmsg=None):
        info = DBYAML.load('info')
        template_value = dict(info=info, errmsg=errmsg)
        
        description = None
        lst = DBYAML.load('description')
        if lst: description = random.choice(lst)
        if description: template_value['description'] = description
        
        html = template.render('tmpl/index.html', template_value)
        self.response.out.write(html)
        
        
    def session_counter(self):
        """連打用のカウンタ"""
        session_id = self.request.cookies.get('session_id')
        if session_id is None:
            session_id = str(random.getrandbits(64))
            expires = datetime.datetime.now() + datetime.timedelta(hours=1)
            expires = expires.strftime('%a, %d %b %Y %H:%M:%S GMT')
            
            self.response.headers.add_header(  
                'Set-Cookie', 'session_id=%s;expires=%s' % (session_id, expires))
            
        memcache.add(key=session_id, value=0, time=120)
        count = memcache.incr(session_id)
        if count is None:
            count = 1
            logging.warning('memcache replace')
            memcache.set(key=session_id, value=1, time=120)

        return count
    
    
    def get(self, action):
        
        cause_error = None
        if action == 'verify':
            conf = DBYAML.load('oauth')
            if not conf: return
            
            now = datetime.datetime.now() + datetime.timedelta(hours=+9)
            logging.info('%s [%s]' % (action, now))
            
            handler = libs.auth.OAuthHandler(handler=self, conf=conf)
            url = handler.login()
            # redirect (not reached)
            
        elif action == 'callback':
            conf = DBYAML.load('oauth')
            if not conf: return
            
            now = datetime.datetime.now() + datetime.timedelta(hours=+9)
            logging.info('%s [%s]' % (action, now))
            
            handler = libs.auth.OAuthHandler(handler=self, conf=conf)
            users_token = handler.callback()
            if users_token:
                
                is_block = False
                blocklist = DBYAML.load('blocklist')
                if blocklist:
                    if users_token._name in blocklist:
                        is_block = True
                        
                if not is_block:
                    # random tweet
                    count  = self.session_counter()
                    result = random_tweet(via=users_token, count=count)
                    
                    if result:
                        # update graph
                        q = taskqueue.Queue('fastest')
                        t = taskqueue.Task(url='/task/graph')
                        q.add(t)
                    else:
                        cause_error = True
                        logging.error('random tweet error!!')
                    
                else:
                    cause_error = True
                    logging.warning('blocking %s' % users_token._name)
                    
            else:
                cause_error = True
                logging.error('callback error!!')
                
            url = '/'
            if cause_error: url = '/error'
            self.redirect(url)
            
        else:
            errmsg = None
            if action == 'error':
                errmsg = 'エラーが発生しました。しばらく待ってからもう一度試してみてください。'
            self.default_page(errmsg=errmsg)



def main():
    application = webapp.WSGIApplication([
            ('^/(.*?)/?$'      , MainHandler ),
            ], debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
