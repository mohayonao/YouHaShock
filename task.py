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

import random
import datetime

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

from google.appengine.api import urlfetch
from google.appengine.api.labs import taskqueue

from model import OAuthRequestToken, OAuthAccessToken


################################################################################
## handler
################################################################################
class TaskHandler(webapp.RequestHandler):
    """定期処理"""
    
    def get(self, action):
        if action == 'request':
            expired = datetime.datetime.now() - datetime.timedelta(minutes=10)
            expired_tokens = OAuthRequestToken.all().filter('created <', expired).fetch(40)
            for token in expired_tokens:
                token.delete()
                
                
        elif action == 'access':
            expired = datetime.datetime.now() - datetime.timedelta(hours=2)
            expired_tokens = OAuthAccessToken.all().filter('modified <', expired).fetch(60)
            
            for i, token in enumerate(expired_tokens):
                key_name = token.key().name()
                taskqueue.add(url='/task/access', params=dict(key_name=key_name), countdown=i)
                
                
                
    def post(self, action):
        if action == 'access':
            key_name = self.request.get('key_name')
            result = self.verify_oauth_token(key_name)
            if not result: self.error(504)
            
            
            
            
    def verify_oauth_token(self, key_name):
        from libs.twitter import OAuth, TwitterAPI
        from model import OAuthAccessTokenCount, DBYAML
        
        ent = OAuthAccessToken.get_by_key_name(key_name)
        if not ent: return True
        
        token  = dict(token        = ent.oauth_token,
                      token_secret = ent.oauth_token_secret)
        
        conf = DBYAML.load('oauth')
        consumer = dict(consumer_key    = conf.get('consumer_key'   ),
                        consumer_secret = conf.get('consumer_secret'))
        
        oauth = OAuth(consumer, token)        
        try:
            TwitterAPI(oauth).verify()
            
        except urlfetch.DownloadError:
            return False
            
        except urlfetch.InvalidURLError:
            ent.delete()
            OAuthAccessTokenCount.add_count(-1)
            return True
            
        else:
            ent.randint = random.randint(0, 1000)
            ent.put() # update
            return True



def main():
    application = webapp.WSGIApplication([
            ('^/cron/(.*?)/?$' , TaskHandler),
            ('^/task/(.*?)/?$' , TaskHandler),
            ], debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
