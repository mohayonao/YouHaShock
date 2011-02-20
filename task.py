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
import logging
import datetime


from google.appengine.ext import webapp
from google.appengine.ext.webapp import util

from google.appengine.ext import db
from google.appengine.api import urlfetch
from google.appengine.api.labs import taskqueue
from django.utils import simplejson

from libs.twitter import OAuth, TwitterAPI

from model import OAuthRequestToken, OAuthAccessToken
from model import YouHaShockHistory
from model import UserStatus
from model import DBYAML


################################################################################
## handler
################################################################################
class CheckedHistory(db.Model):
    checked = db.DateTimeProperty()


class TaskHandler(webapp.RequestHandler):
    """定期処理"""
    
    def get(self, action):
        if action == 'request':
            expired = datetime.datetime.now() - datetime.timedelta(minutes=10)
            expired_tokens = OAuthRequestToken.all().filter('created <', expired).fetch(50)
            for token in expired_tokens:
                token.delete()
                
        elif action == 'access':
            expired = datetime.datetime.now() - datetime.timedelta(hours=4)
            expired_tokens = OAuthAccessToken.all().filter('modified <', expired).fetch(30)
            
            q = taskqueue.Queue('background')
            for i, token in enumerate(expired_tokens):
                key_name = token.key().name()
                t = taskqueue.Task(url='/task/access', params=dict(key_name=key_name), countdown=i*2)
                q.add(t)
        
        elif action == 'graph':
            q = taskqueue.Queue('fastest')
            t = taskqueue.Task(url='/task/graph')
            q.add(t)
            
        elif action == 'image':
            q = taskqueue.Queue('background')
            t = taskqueue.Task(url='/task/image')
            q.add(t)
            
            
            
    def post(self, action):
        if action == 'access':
            key_name = self.request.get('key_name')
            res = self.verify_oauth_token(key_name)
            if not res:
                self.error(504)
                
        elif action == 'graph':
            res = self.update_graph()
            if res:
                q = taskqueue.Queue('fastest')
                t = taskqueue.Task(url='/task/graph')
                q.add(t)
                
        elif action == 'image':
            res = self.update_image()
            if res:
                q = taskqueue.Queue('background')
                t = taskqueue.Task(url='/task/image')
                q.add(t)
                
                
    def update_image(self):
        expired = datetime.datetime.now() - datetime.timedelta(days=2)
        ent = UserStatus.all().filter('profile_image_updated <', expired).get()
        if not ent:
            logging.debug('update_image: None')
            return False
        
        name = ent.key().name()[3:]
        logging.debug('profile_image: %s' % name)
        if not ent.profile_image_url:
            profile_image_url = self.get_profile_image(name)
            ent.profile_image_url = profile_image_url
            logging.debug('profile_image_url: %s' % ent.profile_image_url)
            if not profile_image_url:
                logging.warning('profile_image: %s = NONE' % name)
            
        ent.profile_image_updated = datetime.datetime.now()
        ent.put()
        
        return True
    
    
    def update_graph(self):
        checked = CheckedHistory.get_by_key_name('_')
        if not checked: return False
        
        token = YouHaShockHistory.all().order('created').filter('created >', checked.checked).get()
        if not token: return False
        
        logging.debug('update graph %s > %s [%s]' % (token.from_user, token.to_user, token.created))
        self.update_status(token.from_user, 'call', token.to_user)
        self.update_status(token.to_user, 'callee', token.from_user)
        checked.checked = token.created
        checked.put()
        
        return True
    
    
    def update_status(self, name, type, opposite):
        name     = '%s' % name
        key_name = 'at_%s' % name
        ent = UserStatus.get_by_key_name(key_name)
        if not ent:
            logging.warning('missing user: %s (%s)' % (name, key_name))
            ent = UserStatus(key_name=key_name)
            ent.profile_image_url = self.get_profile_image(name)
            ent.put()
            
        if type == 'call':
            ent.call_count += 1
        elif type == 'callee':
            ent.callee_count += 1

        graph = ent.graph or '{ "call":{},"callee":{} }'
        try:
            graph = eval(graph)
        except TypeError:
            graph = { "call":{}, "callee":{} }
            
        graph_item = graph[type]
        graph_item[opposite] = graph_item.get(opposite, 0) + 1
        ent.graph = str(graph)
        ent.put()
        
        
    def verify_oauth_token(self, key_name):
        from libs.twitter import OAuth, TwitterAPI
        from model import DBYAML
        
        ent = OAuthAccessToken.get_by_key_name(key_name)
        if not ent: return True
        
        token  = dict(token        = ent.oauth_token,
                      token_secret = ent.oauth_token_secret)
        
        conf = DBYAML.load('oauth')
        consumer = dict(consumer_key    = conf.get('consumer_key'   ),
                        consumer_secret = conf.get('consumer_secret'))
        
        oauth = OAuth(consumer, token)        
        try:
            res = TwitterAPI(oauth).verify()
            
        except urlfetch.DownloadError:
            return False
            
        except urlfetch.InvalidURLError:
            logging.debug('delete: access token')
            ent.delete()
            return True
        
        else:
            ent.randint = random.randint(0, 1000)
            ent.put()
            return res
        
        
    def get_profile_image(self, name):
        
        consumer  = DBYAML.load('oauth')
        consumer = dict(consumer_key    = consumer.get('consumer_key'   ),
                        consumer_secret = consumer.get('consumer_secret'))
        
        adminuser = DBYAML.load('adminuser')
        adminuser = dict(token=adminuser.get('oauth_token'),
                         token_secret=adminuser.get('oauth_token_secret'))
        
        oauth = OAuth(consumer, adminuser)
        api = TwitterAPI(oauth)
        
        try:
            res = api.show(screen_name=name)
        except urlfetch.DownloadError:
            return
        
        except urlfetch.InvalidURLError:
            return
        
        if res:
            return res.get('profile_image_url')



def main():
    application = webapp.WSGIApplication([
            ('^/cron/(.*?)/?$' , TaskHandler),
            ('^/task/(.*?)/?$' , TaskHandler),
            ], debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
