import os
import threading
import datetime
import subprocess


class Channel(threading.Thread):
    quality = 'best'

    def __init__(self, thread_id, channel, title, path):
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
        self.thread_id = thread_id
        self._is_running = True
        self.livestreamer_process = None
        self.channel = channel
        self.title = title
        self.path = path
        self.args = ""
        self.start_time = 0
        self.base_url = 'https://www.twitch.tv/'
        self.url = self.base_url + self.channel

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
        # TODO: tell the data structure I am here
        self.start_stream_dl()

        # outside while loop, meaning thread end
        print 'Stream ended: %s - %s (ID: %s)' % (self.get_channel(), self.get_title(), str(self.thread_id))
        # TODO: Tell the data structure I am here no more

    # Thread
    def start_stream_dl(self):
        """
        Start download of stream
        :return:
        """
        self.start_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        self.args = ['-o', '%s%s - %s - %s.ts' % (self.path, self.channel, self.start_time.replace(":", "-"), self.title), self.url, self.quality]

        print "[%s] starting dl: %s - %s" % (self.start_time, self.channel, self.title)
        # Fire up livestreamer instance
        self.livestreamer()


    # To be used from main
    def stop(self):
        """
        Tell channel to stop at earliest convenience (usually when stream download finishes)
        Print attempt to user
        :return:
        """
        print "Stopping %s (%s)" % (self.channel, str(self.thread_id))
        self.livestreamer_process.terminate()

    # To be used from main
    def kill(self):
        print "%s (%s) is being killed with F I R E" % (self.channel, str(self.thread_id))
        self.livestreamer_process.kill()

    # To be used from thread
    def livestreamer(self):
        args_to_start = ['livestreamer'] + self.args
        devnull = open(os.devnull, 'wb')
        try:
            self.livestreamer_process = subprocess.Popen(args_to_start, stdin=devnull,
                                                         stdout=subprocess.PIPE, stderr=devnull)
            self.livestreamer_process.wait()
        except subprocess.CalledProcessError as derp:
            print derp
            pass
        # We'll get here no matter what

    def get_channel(self):
        """
        Returns the name of the channel
        :return:
        """
        return self.channel

    def get_start_time(self):
        """
        Returns the time and date the stream was started
        :return:
        """
        return self.start_time

    def get_title(self):
        """
        Returns the title specified by user
        :return:
        """
        return self.title
