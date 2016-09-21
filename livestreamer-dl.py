# coding=utf-8
import re
from basicio import BasicIO
from channel import Channel
from config import Config # TODO: Config issues
# splitchar = unichr(179);
splitchar = '|'
downloading = []
download_history = []
#cfg = Config() # TODO: Config issues
#path = "X:\\twitch\\dump\\" # TODO: Config issues

__author__ = 'BluABK <abk@blucoders.net>'

cmd_download = ['dl', 'download', 'start', 'get', 'gimme']
cmd_list = ['list', 'downloads', 'downloading']
cmd_history = ['history', 'listraw']
cmd_stop = ['stop', 'end']
cmd_kill = ['kill', 'diaf']
cmd_help = ['help']
cmd_quit = ['q', 'quit', 'exit']


class UI:
    def __init__(self):
        """
        Livestreamer download User Interface
        Note: Currently only supports Twitch TV
        """
        self.run = True
        self.threads = []
        self.io_thread = BasicIO(0)
        self.io_thread.start()
        self.thread_id = 0

        self.prompt()
        print "\nStopping streams... (if this lasts for too long they might have gone rogue)"
        for stream in downloading:
            stream.stop()

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
        while self.run:
            command = raw_input(">: ")
            cmd = command.lower().split(' ')
            if cmd[0] in cmd_download:
                if len(cmd) == 1:
                    channel = raw_input('Channel: ')
                    title = self.query_title()
                    self.download_stream(channel, title)
                else:
                    # Send in command instead of cmd to preserve casing
                    self.download_stream(cmd[1], " ".join(command.split(' ')[2:]))
            elif cmd[0] in cmd_list:
                self.update_downloading()
                self.list_dl()
            elif cmd[0] in cmd_history:
                self.update_downloading()
                self.list_dl_history()
            elif cmd[0] in cmd_stop:
                self.stop_stream(cmd)
            elif cmd[0] in cmd_kill:
                self.kill_stream(cmd)
            elif cmd[0] in cmd_help:
                self.print_help()
            elif cmd[0] in cmd_quit:
                self.run = False

    def download_stream(self, channel, title='Untitled'):
        """
        Downloads a twitch stream based on args
        :param channel:
        :param title:
        :return:
        """
        #title = self.sanify_filename(title) # FIXME: pads *every* character with underscore (WHOOPS!)
        try:
            cur_thread = Channel(self.thread_id, channel, title, "X:\\twitch\\dump\\")  # FIXME: config issues
            # Add to list of downloading streams
            downloading.append(cur_thread)
            download_history.append(cur_thread)
            cur_thread.start()
            self.threads.append(cur_thread)
            self.thread_id += 1
        except SyntaxError as derp:
            print derp.message

    @staticmethod
    def stop_stream(cmd):
        """
        Stops a currently downloading stream
        :param cmd:
        :return:
        """
        print downloading[0].get_thread_id()
        if len(cmd) > 1:
            target = int(cmd[1])
            if target in downloading:
                downloading[target].stop()
                if downloading[target].status():
                    downloading.pop(target)
            else:
                print "No stream with ID %s exists" % cmd[1]
        else:
            print "missing stream ID argument"

    def kill_stream(self, cmd):
        """
        When stopping doesn't work, let's try killing the download with fire
        :param cmd:
        :return:
        """
        if len(cmd) > 1:
            target = int(cmd[1])
            if target in downloading:
                downloading[target].kill()
                if downloading[target].status():
                    downloading.pop(target)
            else:
                # kill_stream() goes that extra mile compared to stop_stream()
                if self.kill_rogue_stream(download_history[target]) is False:
                    print "No stream with ID %s exists" % cmd[1]
        else:
            print "missing stream ID argument"

    @staticmethod
    def kill_rogue_stream(target):
        """
        When killing doesn't work, let's nuke the entire thread from orbit
        :param target:
        :return:
        """
        try:
            channel = target.get_channel()
            tid = target.get_thread_id()
            target.kill()
            print "Killed rogue stream instance: %s (%s) :o" % (channel, tid)
        except:
            # There was nothing to kill
            return False

    @staticmethod
    def list_dl():
        """
        Lists current active downloads
        :return:
        """
        print 'currently downloading:'
        for stream in downloading:
            print 'Stream %s: %s - %s (started at %s)'\
                  % (str(stream.get_thread_id()), stream.get_channel(), stream.get_title(), stream.get_start_time())

    @staticmethod
    def list_dl_history():
        """
        Lists all active and inactive downloads (partly used by kill_rogue_stream())
        :return:
        """
        print 'download history:'
        for stream in download_history:
            if stream.status() is False:
                status = "[ended      ]"
            else:
                status = "[downloading]"
            print 'Stream %s: %s - %s (started at %s) %s' % (str(stream.get_thread_id()), stream.get_channel(),
                                                             stream.get_title(), stream.get_start_time(), status)

    @staticmethod
    def update_downloading():
        """
        Updates the list of currently downloading items by removing dead streams
        :return:
        """
        global downloading
        updated_list = []
        for stream in downloading:
            if stream.status():
                updated_list.append(stream)
        downloading = updated_list

    @staticmethod
    def print_help():
        print 'Available commands'
        print 'dl [channel] [title]                 Download a stream (no args gives interactive prompt)'
        print 'list                                 Lists current active downloads'
        print 'history                              Lists all active and inactive downloads (and their status)'
        print 'stop [ID]                            Ends a stream (NB: Currently out of order)'
        print 'kill [ID]                            Kills a stream (NB: Currently out of order)'
        print 'quit                                 Closes streams and quits the program (NB: Unable to close streams)'
        print 'help                                 Take a guess..'
        print 'Example:  dl northernlion Northern Lion Super Show (Josh day) - The Binding of Isaac'

if __name__ == "__main__":
    UI()
