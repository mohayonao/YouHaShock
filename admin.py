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

from google.appengine.dist import use_library
use_library('django', '1.2')

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util
from google.appengine.ext.webapp import template

from model import DBYAML


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
            
            
    def post(self, action):
        if action == 'edit':
            params = dict(self.request.POST)
            cmd = params.get('submit')
            if cmd == 'SUBMIT':
                name = params.get('name')
                text = params.get('yaml-text')
                logging.info("%s:%s" % (name, text))
                if name and text:
                    try: DBYAML.save(name, yaml.load(text))
                    except: pass
                    
            elif cmd == 'DELETE':
                key_name = '_%s' % params.get('name')
                ent = DBYAML.get_by_key_name(key_name)
                if ent: ent.delete()
        self.redirect('/admin/edit/')



def main():
    application = webapp.WSGIApplication([
            ('^/admin/(.*?)/?$', AdminHandler),
            ], debug=True)
    util.run_wsgi_app(application)


if __name__ == '__main__':
    main()
