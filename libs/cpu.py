#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
from google.appengine.api import quota

class CPUChecker:
    """CPUの使用状況をモニタする"""
    
    def __init__(self, name='CPUChecker'):
        self.name  = name
        self.start = quota.get_request_cpu_usage()
        
        
    def check(self, msg):
        end = quota.get_request_cpu_usage()
        logging.debug('%s: %s (%d megacycles)' % (self.name, msg, end - self.start))
        self.start = end
