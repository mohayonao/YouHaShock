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
import datetime, time

from google.appengine.api import memcache
from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext import db

import libs.timeago



from model import YouHaShockHistory



################################################################################
## misc
################################################################################
def tweet_user_link(name):
    name = name.encode('utf-8')
    return """<a href="http://twitter.com/%s" target="twitter">@%s</a>""" % (name, name)


def tweet_status_link(user, status_id, caption):
    user      = user.encode('utf-8')
    caption   = caption.encode('utf-8')
    return """<i>(<a href="http://twitter.com/%s/status/%s" target="twitter">%s</a>)</i>""" % (user, status_id, caption)



class APIHandler(webapp.RequestHandler):
    """API"""
    
    def get(self, action):
        if action == 'history2':
            
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
            
        elif action == 'history':
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



def main():
    application = webapp.WSGIApplication([
            ('^/api/(.*?)/?$', APIHandler),
            ], debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
