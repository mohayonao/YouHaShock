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

import yaml
import logging

# from google.appengine.dist import use_library
# use_library('django', '1.2')

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template

from model import DBYAML


from libs.twitter import OAuth, TwitterAPI


class AdminHandler(webapp.RequestHandler):
    """管理者用ページ"""
    
    def get(self, action):

        action = action.split('/')
        action, args = action[0], action[1:]
        
        if action == 'edit':
            filelist = DBYAML.catalog()
            html = template.render('tmpl/edit.html', { 'filelist': filelist })
            self.response.out.write(html)
            
        elif action == 'load' and args:
            self.response.out.write(DBYAML.loadtext(name=args[0]))
            
        elif action == 'test':
            import yaml
            
            d = {}
            for ent in DBYAML.all():
                k = ent.key().name()
                if k.startswith('_'): 
                    k = k[1:]
                    d[k] = yaml.load(ent.yaml_text)
            logging.info(d)
            
            yaml_text = yaml.safe_dump(d, encoding='utf8',
                                       allow_unicode=True,
                                       default_flow_style=False)
            yaml_text = yaml_text.decode('utf-8')
            
            e = DBYAML(key_name='settings')
            e.yaml_text = yaml_text
            e.put()
            
            
            
    def post(self, action):
        if action == 'edit':
            params = dict(self.request.POST)
            cmd = params.get('submit')
            if cmd == 'SUBMIT':
                name = params.get('name')
                text = params.get('yaml-text')
                logging.info("%s:%s" % (name, text))
                DBYAML.save(name, text)
                
            elif cmd == 'DELETE':
                DBYAML.delete(params.get('name'))
                
        self.redirect('/admin/edit/')
        
        

        




def main():
    application = webapp.WSGIApplication([
            ('^/admin/(.*?)/?$', AdminHandler),
            ], debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
