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
        self.zombies = []

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
            self.zombies.append(self.list[index])
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
