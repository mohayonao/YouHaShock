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

import logging
import time

from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext import db


from model import YouHaShockHistory
from model import UserStatus
from model import DBYAML


################################################################################
## misc
################################################################################
class APIHandler(webapp.RequestHandler):
    """API"""

    def get_history(self):
        """履歴を返す"""
        
        try: cursor = int(self.request.get('cursor', 0))
        except ValueError: cursor = 0
        
        try: limit = int(self.request.get('limit', 0))
        except ValueError: limit = 0
        
        q = db.Query(YouHaShockHistory)
        if cursor == 0:
            limit = 20
        elif limit:
            where = 'status_id %s' % ('>' if limit < 0 else '<')
            q = q.filter(where, cursor)
            
        q = q.order('-status_id')
        
        self.response.out.write('{')
        
        limit = abs(limit)
        entities = q.fetch(limit + 1)
        has_next = (len(entities) > limit)
        
        self.response.out.write('n:%s,' % ('true' if has_next else 'false'))
        
        self.response.out.write('"list":[')            
        for ent in entities[:limit]:
            id = ent.status_id
            d =  time.mktime(ent.created.timetuple())
            self.response.out.write('["%s","%s","%s","%s",%s],' % (ent.from_user, ent.to_user, ent.word, id, d))
            
        self.response.out.write(']}')
        
        
    def get_image_url(self):
        """アイコン画像のURLを返す"""
        
        name = self.request.get('name')
        if not name: return 'null'

        key_name = 'at_%s' % name
        url = memcache.get(key=key_name)
        if not url:
            ent = UserStatus.get_by_key_name(key_name)
            if not ent: return 'null'
            url = ent.profile_image_url
            memcache.set(key=key_name, value=url)
        self.response.out.write(url)
        
        
    def get_graph(self):
        """ユーザーグラフを返す"""
        
        name = self.request.get('name')
        if not name: return 'null'
        
        key_name = 'at_%s' % name
        ent = UserStatus.get_by_key_name(key_name)
        if not ent: return 'null'


        self.response.out.write('{')
        self.response.out.write('img:"%s",' % (ent.profile_image_url))
        self.response.out.write('call:%d,callee:%d,' % (ent.call_count, ent.callee_count))
        
        if ent.graph:
            try: graph = eval(ent.graph)
            except TypeError: graph = { }
            self.response.out.write('graph:{')
            
            call = graph.get('call', {})
            self.response.out.write('call:{')
            for k, v in call.iteritems():
                self.response.out.write('"%s":%s,' % (k, v))
            self.response.out.write('},')
            
            callee = graph.get('callee', {})
            self.response.out.write('callee:{')
            for k, v in callee.iteritems():
                self.response.out.write('"%s":%s,' % (k, v))
            self.response.out.write('},')
            
            self.response.out.write('}')
            
        self.response.out.write('}')
        
        
    def get_ranking(self):
        """ランキングを返す"""
        
        blocklist = DBYAML.load('blocklist')
        
        def write_user_ranking(type, limit):
            key_name = 'ranking_%s' % type
            lst = memcache.get(key_name)
            if not isinstance(lst, list):
                lst = []
                if type == 'call':
                    query = UserStatus.all().order('-call_count')
                else:
                    query = UserStatus.all().order('-callee_count')
                    
                for ent in query:
                    name = ent.key().name()[3:]
                    if name in blocklist: continue

                    profile_image_url = ent.profile_image_url
                    if type == 'call':
                        count = ent.call_count
                    else:
                        count = ent.callee_count
                    lst.append( (name, profile_image_url,count) )
                    limit -= 1
                    if limit < 0: break
                memcache.set(key=key_name, value=lst, time=120)
                
            for l in lst:
                self.response.out.write("['%s','%s',%d]," % (l[0], l[1], l[2]))
                
        
        try: limit = int(self.request.get('limit', 5))
        except ValueError: limit = 5
        
        self.response.out.write('{')
        self.response.out.write('call:[')
        write_user_ranking('call', limit)
        self.response.out.write('],')
        
        self.response.out.write('callee:[')
        write_user_ranking('callee', limit)
        self.response.out.write('],')
        
        self.response.out.write('}')
        
        
        
    def get(self, action):
        if action == 'history2':
            self.get_history()
        elif action == 'image':
            self.get_image_url()
        elif action == 'graph':
            self.get_graph()
        elif action == 'ranking':
            self.get_ranking()
            
            
def main():
    application = webapp.WSGIApplication([
            ('^/api/(.*?)/?$', APIHandler),
            ], debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
