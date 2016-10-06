import os
import threading
import datetime
import subprocess


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

    """ Thread uses these variables:
        - self.start_time
        - self.args
        - self.livestreamer_process
        - probably self.end_time
    """
    """ Main uses these variables:
        - all the ones in init, but we don't care about that
        - self.livestreamer_process
    """
    """
        - Strictly speaking, everything should really be locked away in mutexes
        - this is not an OS kernel so we can rule out unlikely or unimportant errors
    """

    # Thread
    def run(self):
        """
        Thread runtime
        :return:
        """
        self.thread_id = self.threads.add(self)
        self.start_stream_dl()
        # This also adds us to the cleanup queue
        self.threads.remove(self.thread_id)

    # Thread
    def start_stream_dl(self):
        """
        Start download of stream
        :return:
        """
        self.start_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')

        print("[%s] starting dl: %s - %s" % (self.start_time, self.channel, self.title))
        # Fire up livestreamer instance
        self.livestreamer()

        self.end_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        print('[%s] Stream ended: %s - %s (ID: %d)' % (self.end_time, self.channel, self.title, self.thread_id))

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
        url = self.base_url + self.channel
        args_to_start = ['livestreamer',
                         '-o',
                         '%s%s - %s - %s.ts' % (self.path, self.channel, self.start_time.replace(":", "-"), self.title),
                         url, self.quality]
        try:
            # Might set stderr=subprocess.PIPE for later fun
            self.livestreamer_process = subprocess.Popen(args_to_start, stdin=subprocess.DEVNULL,
                                                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            self.livestreamer_process.wait()
        except subprocess.CalledProcessError as derp:
            print(derp)
            return False
