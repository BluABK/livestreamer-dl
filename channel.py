from __future__ import division
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

    def run(self):  # FIXME: Overrides method in Thread (Intentional?)
        """
        Thread runtime
        :return:
        """
        while self._is_running:
            self.start_stream_dl()

        # outside while loop, meaning thread end
        print 'thread ' + str(self.thread_id) + ' ended'

    def start_stream_dl(self):
        """
        Start download of stream
        :return:
        """
        self.start_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        self.args = '-o "%s%s - %s - %s".ts %s %s' % (self.path, self.channel, self.start_time.replace(":", "-"),
                                                      self.title, self.url, self.quality)
        print "[%s] starting dl: %s - %s" % (self.start_time, self.channel, self.title)
        # Fire up livestreamer instance
        self.livestreamer()

    def stop(self):
        """
        Tell channel to stop at earliest convenience (usually when stream download finishes)
        :return:
        """
        print "Stopping %s (%s)" % (self.channel, str(self.thread_id))
        self.livestreamer_process.terminate()
        # self._stop.set()
        self._is_running = False

    def status(self):
        """
        Returns status about whether the thread is running or not (may be false if external process still runs)
        :return:
        """
        return self._is_running

    def kill(self):
        print "%s (%s) is being killed with F I R E" % (self.channel, str(self.thread_id))
        self.livestreamer_process.kill()
        self._is_running = False

    def livestreamer(self):
        args_to_start = 'livestreamer ' + self.args
        try:
            self.livestreamer_process = subprocess.Popen(args_to_start, shell=True, stdout=subprocess.PIPE)
            self.livestreamer_process.communicate()
        except subprocess.CalledProcessError as derp:
            print derp
            return False
        # When process ends
        return True

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

    def get_thread_id(self):
        """
        Returns the thread number
        :return:
        """
        return self.thread_id

    def get_title(self):
        """
        Returns the title specified by user
        :return:
        """
        return self.title



