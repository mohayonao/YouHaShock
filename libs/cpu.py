#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from google.appengine.api import quota

class CPUChecker:
    """CPUの使用状況をモニタする"""
    
    def __init__(self, name='CPUChecker', lv=logging.DEBUG):
        self.name  = name
        self.lv    = lv
        self.start = quota.get_request_cpu_usage()

    def kokokara(self, msg=None):
        if msg: logging.log(self.lv, msg)
        self.start = quota.get_request_cpu_usage()
        
    def kokomade(self, msg):
        end = quota.get_request_cpu_usage()
        logging.log(self.lv, '%s: %s (%d megacycles)' % (self.name, msg, end - self.start))
        self.start = end
        
        
