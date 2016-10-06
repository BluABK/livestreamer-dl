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
        self.history = {}
        self.it = 0
        self.mutex = threading.Lock()
        self.zombies = []

    def add(self, obj, channel, title, path, start_time):
        self.mutex.acquire()
        try:
            index = self.it
            self.it += 1
            self.list[index] = obj
            self.history[index] = ChannelLog(index, channel, title, path, start_time)
            return index
        finally:
            self.mutex.release()

    def get(self, index):
        self.mutex.acquire()
        try:
            return self.list[index]
        finally:
            self.mutex.release()

    def remove(self, index, end_time):
        self.mutex.acquire()
        try:
            self.zombies.append(self.list[index])
            self.history[index].finished(end_time)
            del self.list[index]
        finally:
            self.mutex.release()

    def threads(self):
        self.mutex.acquire()
        try:
            return dict(self.list)
        finally:
            self.mutex.release()

    def pop_zombies(self):
        self.mutex.acquire()
        try:
            ret = list(self.zombies)
            self.zombies = []
            return ret
        finally:
            self.mutex.release()

    def get_history(self):
        self.mutex.acquire()
        try:
            return dict(self.history)
        finally:
            self.mutex.release()

class ChannelLog():
    def __init__(self, thread_id, channel, title, path, start_time):
        self.thread_id = thread_id
        self.channel = channel
        self.title = title
        self.path = path
        self.start_time = start_time
        self.end_time = None
        self.active = True

    def finished(self, end_time):
        self.end_time = end_time
        self.active = False

    def print_status(self):
        if not self.active:
            status = "[ended      ]"
        else:
            status = "[downloading]"

        if not self.active:
            extra = " (ended at %s)" % self.end_time
        else:
            extra = ""

        print(status+" Stream %d: %s - %s (started at %s)%s" %
                (self.thread_id, self.channel, self.title, self.start_time, extra))
