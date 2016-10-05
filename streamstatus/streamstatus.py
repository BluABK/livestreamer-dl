#!/usr/bin/env python

import threading


class ChannelStatus():
    """
    Important tidbit:
        You have to lock *ALL THE WAY* from you start reading until you write back.
        If you only lock before one read or write, then this can happen:
            a reads
            b reads
            a writes (information without a, but with b)
            b writes (information without b, but with a)

            and it's as if a never cleaned up at all.
    """
    def __init__(self):
        self.list = {}
        self.it = 0
        self.mutex = threading.Lock()

    def add(self, obj):
        self.mutex.acquire()
        try:
            index = self.it
            self.it += 1
            self.list[index] = obj
            return index
        finally:
            self.mutex.release()

    def get(self, index):
        self.mutex.acquire()
        try:
            return self.list[index]
        finally:
            self.mutex.release()

    def remove(self, index):
        self.mutex.acquire()
        try:
            del self.list[index]
        finally:
            self.mutex.release()

    def list(self):
        self.mutex.acquire()
        try:
            return self.list[:]
        finally:
            self.mutex.release()

bleh = ChannelStatus()
# Threads add themselves and stores the idx they get.
# in your thread:
#    self.index = channelstatus.add(self)
# Before exiting, threads delete themselves:
#    channelstatus.remove(self.index)

# If main wants a list of indexes:
#    running = channelstatus.list()
# Then if main wants a thread gone:
#    channelstatus.get(index).pleasedie()
# The thread should clean up when it's done.
# MAIN IS NOT YOUR MOM! Thread cleans up its own mess!
# Thread can print to stdout. This becomes push notifications.

bleh.add("meh")
bleh.add("meh2")

print bleh.list
