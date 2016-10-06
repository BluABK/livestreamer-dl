#!/usr/bin/env python3
# coding=utf-8
import time
import re

from channelstatus import ChannelStatus
from channel import Channel
from config import Config # TODO: Config issues

# splitchar = unichr(179);
splitchar = '|'
#cfg = Config() # TODO: Config issues
#path = "X:\\twitch\\dump\\" # TODO: Config issues

__author__ = 'BluABK <abk@blucoders.net>'

# FIXME: config issues
outdir = "X:\\twitch\\dump\\"

class UI:
    def __init__(self):
        """
        Livestreamer download User Interface
        Note: Currently only supports Twitch TV
        """
        self.threads = ChannelStatus()

    def __del__(self):
        print("\nTelling streams to stop")
        for tid, stream in self.threads.threads().items():
            stream.stop()
        print("Waiting for streams", end='')
        while len(self.threads.threads()):
            print('.', end='')
            time.sleep(1)
        print(" done")
        self.handle_zombies()

    def handle_zombies(self):
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
        command = input(">: ")
        cmd = command.lower().split(' ')
        if cmd[0] in ['dl', 'download', 'start', 'get', 'gimme']:
            if len(cmd) == 1:
                channel = raw_input('Channel: ')
                title = self.query_title()
                self.download_stream(channel, title)
            else:
                # Send in command instead of cmd to preserve casing
                self.download_stream(cmd[1], " ".join(command.split(' ')[2:]))
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

    def download_stream(self, channel, title='Untitled'):
        """
        Downloads a twitch stream based on args
        :param channel:
        :param title:
        :return:
        """
        #title = self.sanify_filename(title) # FIXME: pads *every* character with underscore (WHOOPS!)
        try:
            Channel(self.threads, channel, title, outdir).start()
        except SyntaxError as derp:
            print(derp.message)

    def stop_stream(self, cmd):
        """
        Stops a currently downloading stream
        :param cmd:
        :return:
        """
        if len(cmd) < 2:
            print("missing stream ID argument")
            return
        self.threads.get(int(cmd[1])).stop()
        #print("No stream with ID %s exists" % cmd[1]) TODO

    def kill_stream(self, cmd):
        """
        When stopping doesn't work, let's try killing the download with fire
        :param cmd:
        :return:
        """
        if len(cmd) < 2:
            print("missing stream ID argument")
            return
        self.threads.get(int(cmd[1])).kill()
        #print("No stream with ID %s exists" % cmd[1]) TODO

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

if __name__ == "__main__":
    ui = UI()
    while ui.prompt():
        ui.handle_zombies()
    del ui
