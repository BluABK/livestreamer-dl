#!/usr/bin/env python3
# coding=utf-8

# Compatibility
from __future__ import print_function
from sys import version_info
import time
import re

from channelstatus import ChannelStatus
from channel import Channel

if version_info[0] == 3:
    from config import Config # TODO: Config issues
elif version_info[0] == 2:
    from ConfigParser import RawConfigParser
    input = raw_input




# splitchar = unichr(179);
splitchar = '|'
#cfg = Config() # TODO: Config issues
#path = "X:\\twitch\\dump\\" # TODO: Config issues

__author__ = 'BluABK <abk@blucoders.net>'

# FIXME: config issues
out_dir = "X:\\twitch\\dump\\"


class UI:
    def __init__(self):
        """
        Livestreamer download User Interface
        Note: Currently only supports Twitch TV
        """
        self.threads = ChannelStatus()

    def __enter__(self):
        return self

    def __exit__(self, exct_type, exce_value, traceback):
        """
        Destructor starts with kindly telling streams to stop, and then it
        waits until the remaining threads are finished.
        """
        print("\nTelling streams to stop")
        for tid, stream in self.threads.threads().items():
            stream.stop()
        print("\nWaiting for streams:")
        while len(self.threads.threads()):
            print('.', end='') # COMPAT: print_function from __future___
            time.sleep(1)
        print("\ndone.")
        self.handle_zombies()

    def handle_zombies(self):
        """
        Zombies are not urgent, but it is important to collect them in the long run.
        Handling them in between prompts will keep this in check.
        """
        for zombie in self.threads.pop_zombies():
            zombie.join()

    @staticmethod
    def sanify_filename(sentence):
        """
        Replaces filename unfriendly characters with underscores
        :param sentence:
        :return:
        """
        return re.sub("[^A-Za-z0-9_.\s-]*", '_', sentence)

    @staticmethod
    def query_title():
        """
        Prompt user for title until they accept their decision
        :return:
        """
        while True:
            title = raw_input("Title: ")
            if title is ' 'or title is '' or title is None:
                title = 'untitled'
                choice = raw_input("No title specified, do you want to download it untitled? (Y/N): ")
                # What the user enters doesn't really matter, unless it is 'n' which indicates they changed decision.
                if choice.lower() is 'n':
                    # Loop around to request a new title
                    continue
            return title

    def prompt(self):
        """
        Interactive user prompt
        :return:
        """
        try:
            command = input(">: ")
        except EOFError:
            return False
        cmd = command.lower().split(' ')
        if cmd[0] in ['dl', 'download', 'start', 'get', 'gimme']:
            if len(cmd) == 1:
                channel = raw_input('Channel: ')
                title = self.query_title()
                self.download_stream(channel, title)
            else:
                # Send in command instead of cmd to preserve casing
                self.download_stream(cmd[1], " ".join(command.split(' ')[2:]))
        elif cmd[0] is 'gimme2':
            if len(cmd) == 1:
                channel = raw_input('Channel: ')
                title = self.query_title()
                self.download_stream(channel, title, method='module')
            else:
                # Send in command instead of cmd to preserve casing
                self.download_stream(cmd[1], " ".join(command.split(' ')[2:]), method='module')
        elif cmd[0] in ['list', 'downloads', 'downloading']:
            self.list_dl()
        elif cmd[0] in ['history', 'listraw']:
            self.list_dl_history()
        elif cmd[0] in ['stop', 'end']:
            self.stop_stream(cmd)
        elif cmd[0] in ['kill', 'diaf']:
            self.kill_stream(cmd)
        elif cmd[0] in ['help']:
            self.print_help()
        elif cmd[0] in ['q', 'quit', 'exit']:
            return False
        return True

    def list_dl_history(self):
        """
        threads also stores history (see ChannelLog in channelstatus.py)
        It contains its own print method that we can access from here.
        """
        for tid, log in self.threads.get_history().items():
            # See channelstatus.ChannelLog.print_status
            log.print_status()

    def download_stream(self, channel, title='Untitled', method=None):
        """
        Downloads a twitch stream based on args
        :param channel:
        :param title:
        :return:
        """
        #title = self.sanify_filename(title) # FIXME: pads *every* character with underscore (WHOOPS!)
        try:
            if method is not None:
                Channel(self.threads, channel, title, out_dir, method=method).start()
            else:
                Channel(self.threads, channel, title, out_dir).start()
        except SyntaxError as derp:
            print(derp.msg)  # was '.message' o0

    def stop_stream(self, cmd):
        """
        Stops a currently downloading stream
        :param cmd:
        :return:
        """
        if len(cmd) < 2:
            print("missing stream ID argument")
            return
        try:
            self.threads.get(int(cmd[1])).stop()
        except KeyError:
            print("No stream with ID %d exists" % int(cmd[1]))

    def kill_stream(self, cmd):
        """
        When stopping doesn't work, let's try killing the download with fire
        :param cmd:
        :return:
        """
        if len(cmd) < 2:
            print("missing stream ID argument")
            return
        try:
            self.threads.get(int(cmd[1])).kill()
        except KeyError:
            print("No stream with ID %d exists" % int(cmd[1]))

    def list_dl(self):
        """
        Lists current active downloads
        :return:
        """
        print('currently downloading:')
        for tid, stream in self.threads.threads().items():
            print('Stream %d: %s - %s (started at %s)'\
                  % (tid, stream.channel, stream.title, stream.start_time))

    @staticmethod
    def print_help():
        print('Available commands')
        print('dl [channel] [title]                 Download a stream (no args gives interactive prompt)')
        print('list                                 Lists current active downloads')
        print('history                              Lists all active and inactive downloads (and their status)')
        print('stop [ID]                            Ends a stream (NB: Currently out of order)')
        print('kill [ID]                            Kills a stream (NB: Currently out of order)')
        print('quit                                 Closes streams and quits the program (NB: Unable to close streams)')
        print('help                                 Take a guess..')
        print('Example:  dl northernlion Northern Lion Super Show (Josh day) - The Binding of Isaac')
        print('')
        print('Developer features:')
        print('gimme2                               Download a stream using livestreamer module instead of shellex')

if __name__ == "__main__":
    with UI() as ui:
        while ui.prompt():
            ui.handle_zombies()
