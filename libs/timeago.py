#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime

_NOW = datetime.utcnow

_SECONDS_PER_MINUTE = 60
_SECONDS_PER_HOUR   = 60 * 60

def _elapsed(delta):
    seconds = delta.seconds
    days = delta.days
    
    hours, seconds = divmod(seconds, _SECONDS_PER_HOUR)
    minutes, seconds = divmod(seconds, _SECONDS_PER_MINUTE)
    
    if seconds >= 30:
        minutes += 1
        seconds = 0
        
    if minutes >= 60:
        hours += 1
        minutes = 0
        
    if minutes >= 30 and hours:
        hours += 1
        minutes = 0
        
    if hours >= 24:
        days += 1
        hours = 0
        
    if hours >= 12 and days:
        days += 1
        hours = 0
        
    if days:
        return days, 0, 0, 0
    
    if hours:
        return 0, hours, 0, 0
    
    if minutes:
        return 0, 0, minutes, 0
    
    return 0, 0, 0, seconds


def get_elapsed(timestamp):
    if timestamp is None:
        return u'不明'
    
    delta = _NOW() - timestamp
    days, hours, minutes, seconds = _elapsed(delta)
    
    if days:
        return u'%d 日前' % days
    elif hours:
        return u'%d 時間前' % hours
    elif minutes:
        return u'%d 分前' % minutes
    
    elif seconds < 10:
        return u'今'
    return u'%s 秒前' % seconds

