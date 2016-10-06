import os
import threading
import datetime
import subprocess
from sys import version_info

if version_info[0] == 3:
    devnull = subprocess.DEVNULL
elif version_info[0] == 2:
    devnull = open(os.devnull, 'wb')


class Channel(threading.Thread):
    quality = 'best'

    def __init__(self, threads, channel, title, path):
        """
        Channel class
        :param thread_id:
        :param channel:
        :param title:
        :param path:
        """
        threading.Thread.__init__(self)
        if channel is None:
            raise SyntaxError("Channel(): No channel Specified ... Whoops!")  # TODO: Create custom Exception
        self.threads = threads
        self.thread_id = None
        self.livestreamer_process = None
        self.channel = channel
        self.title = title
        self.path = path
        self.start_time = None
        self.end_time = None
        self.base_url = 'https://www.twitch.tv/'

    # Thread
    def run(self):
        """
        Thread runtime
        :return:
        """
        # Start time
        self.start_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

        # Register
        self.thread_id = self.threads.add(self, self.channel, self.title, self.path, self.start_time)
        print("[%s] starting dl: %s - %s" % (self.start_time, self.channel, self.title))

        self.livestreamer()

        # Deregister
        self.end_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        print('[%s] Stream ended: %s - %s (ID: %d)' % (self.end_time, self.channel, self.title, self.thread_id))
        self.threads.remove(self.thread_id, self.end_time)

    # To be used from main
    def stop(self):
        """
        Tell channel to stop at earliest convenience (usually when stream download finishes)
        Print attempt to user
        :return:
        """
        print("Stopping %s (%d)" % (self.channel, self.thread_id))
        self.livestreamer_process.terminate()

    # To be used from main
    def kill(self):
        print("%s (%d) is being killed with F I R E" % (self.channel, self.thread_id))
        self.livestreamer_process.kill()

    # To be used from thread
    def livestreamer(self):
        """
        Start a livestreamer instance using shell execute on the livestreamer binary
        :return:
        """
        url = self.base_url + self.channel
        args_to_start = ['livestreamer',
                         '-o',
                         '%s%s - %s - %s.ts' % (self.path, self.channel, self.start_time.replace(":", "-"), self.title),
                         url, self.quality]
        try:
            # Might set stderr=subprocess.PIPE for later fun
            self.livestreamer_process = subprocess.Popen(args_to_start, stdin=devnull,
                                                         stdout=devnull, stderr=devnull)
            self.livestreamer_process.wait()
        except subprocess.CalledProcessError as derp:
            print(derp)
            return False

    def livestreamer_m(self):
        """
        Start a livestreamer instance using the imported livestreamer python script
        :return:
        """
        print("NOT IMPLEMENTED")
