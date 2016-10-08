import os
import signal
import contextlib
import functools
import itertools
import time
import collections

try:
    from livestreamer import (Livestreamer, StreamError, PluginError, NoPluginError)
    import livestreamer_cli.argparser as argparser
    import livestreamer_cli.constants as constants
    import livestreamer_cli.output as output
except ImportError:
    print("Please use pip / pip3 install livestreamer to install livestreamer.")
    raise

class ProgressException(Exception):
    def __init__(self, written, elapsed, speed):
        super(ProgressException, self).__init__("Don't worry, I'm only here to tell you things are okay"
                                                " and give you a small update.")
        self.written = written
        self.elapsed = elapsed
        self.speed = speed


class Progress:
    def __init__(self, iterator):
        """Progress an iterator and updates a pretty status line to a pretty exception.

        The status line contains:
         - Amount of data read from the iterator
         - Time elapsed
         - Average speed, based on the last few seconds.
        """
        speed_updated = start = time.time()
        speed_written = written = 0
        speed_history = collections.deque(maxlen=5)

        for data in iterator:
            yield data

            now = time.time()
            elapsed = now - start
            written += len(data)

            speed_elapsed = now - speed_updated
            if speed_elapsed >= 0.5:
                speed_history.appendleft((
                    written - speed_written,
                    speed_updated,
                ))

                speed_history_written = sum(h[0] for h in speed_history)
                speed_history_elapsed = now - speed_history[-1][1]
                speed = speed_history_written / speed_history_elapsed

                raise ProgressException(self.format_filesize(written),
                                        self.format_time(elapsed),
                                        self.format_filesize(speed))

    @staticmethod
    def format_filesize(size):
        """Formats the file size into a human readable format."""
        for suffix in ("bytes", "kiB", "MiB", "GiB", "TiB"):
            if size < 1024.0:
                if suffix in ("GiB", "TiB"):
                    return "%3.2f %s" % (size, suffix)
                else:
                    return "%3.1f %s" % (size, suffix)
            size /= 1024.0

    @staticmethod
    def format_time(elapsed):
        """Formats elapsed seconds into a human readable format."""
        hours = int(elapsed / (60 * 60))
        minutes = int((elapsed % (60 * 60)) / 60)
        seconds = int(elapsed % 60)

        rval = ""
        if hours:
            rval += str(hours)+"h"

        if elapsed > 60:
            rval += str(minutes)+"m"

        rval += str(seconds)+"s"
        return rval

class LivestreamerClient:
    def __init__(self, output_arg, url_arg, quality_arg):
        self.livestreamer = Livestreamer()
        if os.path.isdir(constants.PLUGINS_DIR):
            self.livestreamer.load_plugins(os.path.expanduser(constants.PLUGINS_DIR))

        arglist = ['-o', output_arg, url_arg, quality_arg]
        # === config files
        config_files = []
        try:
            config_files += [fn+"."+self.livestreamer.resolve_url(url_arg).module for fn in constants.CONFIG_FILES]
        except NoPluginError:
            raise
        # Only load first available default config
        for config_file in filter(os.path.isfile, constants.CONFIG_FILES):
            arglist = ["@" + config_file] + arglist
            break

        self.args = argparser.parser.parse_args(arglist)

        # Handle SIGTERM just like SIGINT
        signal.signal(signal.SIGTERM, signal.default_int_handler)

        # set up some options and launch
        self.setup_http_session()
        self.setup_options()
        self.setup_plugin_options()
        self.handle_url()

    def setup_http_session(self):
        """Sets the global HTTP settings, such as proxy and headers."""
        a = self.args
        ls = self.livestreamer
        ls.set_option("http-proxy",        a.http_proxy                  ) if a.http_proxy
        ls.set_option("https-proxy",       a.https_proxy                 ) if a.https_proxy
        ls.set_option("http-cookies",      dict(a.http_cookie)           ) if a.http_cookie
        ls.set_option("http-headers",      dict(a.http_header)           ) if a.http_header
        ls.set_option("http-query-params", dict(a.http_query_param)      ) if a.http_query_param
        ls.set_option("http-trust-env",    False                         ) if a.http_ignore_env
        ls.set_option("http-ssl-verify",   False                         ) if a.http_no_ssl_verify
        ls.set_option("http-ssl-cert",     a.http_ssl_cert               ) if a.http_ssl_cert
        ls.set_option("http-ssl-cert",     tuple(a.http_ssl_cert_crt_key)) if a.http_ssl_cert_crt_key
        ls.set_option("http-timeout",      a.http_timeout                ) if a.http_timeout

    def setup_options(self):
        """Sets Livestreamer options."""
        a = self.args
        ls = self.livestreamer

        ls.set_option("hls-live-edge",           a.hls_live_edge          ) if a.hls_live_edge
        ls.set_option("hls-segment-attempts",    a.hls_segment_attempts   ) if a.hls_segment_attempts
        ls.set_option("hls-segment-threads",     a.hls_segment_threads    ) if a.hls_segment_threads
        ls.set_option("hls-segment-timeout",     a.hls_segment_timeout    ) if a.hls_segment_timeout
        ls.set_option("hls-timeout",             a.hls_timeout            ) if a.hls_timeout
        ls.set_option("hds-live-edge",           a.hds_live_edge          ) if a.hds_live_edge
        ls.set_option("hds-segment-attempts",    a.hds_segment_attempts   ) if a.hds_segment_attempts
        ls.set_option("hds-segment-threads",     a.hds_segment_threads    ) if a.hds_segment_threads
        ls.set_option("hds-segment-timeout",     a.hds_segment_timeout    ) if a.hds_segment_timeout
        ls.set_option("hds-timeout",             a.hds_timeout            ) if a.hds_timeout
        ls.set_option("http-stream-timeout",     a.http_stream_timeout    ) if a.http_stream_timeout
        ls.set_option("ringbuffer-size",         a.ringbuffer_size        ) if a.ringbuffer_size
        ls.set_option("rtmp-proxy",              a.rtmp_proxy             ) if a.rtmp_proxy
        ls.set_option("rtmp-rtmpdump",           a.rtmp_rtmpdump          ) if a.rtmp_rtmpdump
        ls.set_option("rtmp-timeout",            a.rtmp_timeout           ) if a.rtmp_timeout
        ls.set_option("stream-segment-attempts", a.stream_segment_attempts) if a.stream_segment_attempts
        ls.set_option("stream-segment-threads",  a.stream_segment_threads ) if a.stream_segment_threads
        ls.set_option("stream-segment-timeout",  a.stream_segment_timeout ) if a.stream_segment_timeout
        ls.set_option("stream-timeout",          a.stream_timeout         ) if a.stream_timeout
        ls.set_option("subprocess-errorlog",         a.subprocess_errorlog)

    def setup_plugin_options(self):
        """Sets Livestreamer plugin options."""
        a = self.args
        ls = self.livestreamer

        ls.set_plugin_option("twitch",      "cookie",            a.twitch_cookie                ) if a.twitch_cookie
        ls.set_plugin_option("twitch",      "oauth_token",       a.twitch_oauth_token           ) if a.twitch_oauth_token
        ls.set_plugin_option("ustreamtv",   "password",          a.ustream_password             ) if a.ustream_password
        ls.set_plugin_option("crunchyroll", "username",          a.crunchyroll_username         ) if a.crunchyroll_username
        ls.set_plugin_option("crunchyroll", "password",          a.crunchyroll_password         ) if a.crunchyroll_password
        ls.set_plugin_option("crunchyroll", "purge_credentials", a.crunchyroll_purge_credentials) if a.crunchyroll_purge_credentials
        ls.set_plugin_option("livestation", "email",             a.livestation_email            ) if a.livestation_email
        ls.set_plugin_option("livestation", "password",          a.livestation_password         ) if a.livestation_password

    def handle_url(self):
        """The URL handler.
        Attempts to resolve the URL to a plugin and then attempts
        to fetch a list of available streams.
        Proceeds to handle stream if user specified a valid one,
        otherwise output list of valid streams.
        """
        try:
            streams = self.fetch_streams()
        except NoPluginError:
            raise
        except PluginError:
            raise
        if not streams:
            raise Exception("No streams found on this URL: " + self.args.url)

        self.handle_stream(streams)

    def fetch_streams(self):
        """Attempts to fetch streams until some are returned.
           args.retry_streams - seconds between each attempt
        """
        plugin = self.livestreamer.resolve_url(self.args.url)
        retry_sec = self.args.retry_streams

        try:
            streams = plugin.get_streams(stream_types=self.args.stream_types,
                                         sorting_excludes=self.args.stream_sorting_excludes)
        except PluginError:
            # TODO: This is what happens when we cannot start streaming right away
            raise

        if not streams and not retry_sec:
            # Give up if we aren't told to keep trying
            return None

        while not streams:
            time.sleep(retry_sec)
            try:
                streams = plugin.get_streams(stream_types=self.args.stream_types,
                                             sorting_excludes=self.args.stream_sorting_excludes)
            except PluginError:
                # TODO: This is what happens for every failed retry
                pass
        return streams

    def handle_stream(self, streams):
        """ - Outputs stream data to selected output """
        available = sorted(streams.keys())

        # Improved: Try all the ones you specified,
        stream_names = []
        for name in self.args.stream:
            if name in available:
                stream_names.append(self.resolve_stream_name(streams, name))

        # and their _alt fallbacks
        alts = []
        for name in stream_names:
            if name + "_alt" in available:
                alts += name + "_alt"

        stream_names += alts

        for name in stream_names:
            if self.output_stream(streams[name]):
                return

        raise Exception("The specified stream(s) '%s' could not be found" % ", ".join(self.args.stream))


    @staticmethod
    def resolve_stream_name(streams, stream_name):
        """Returns the real stream name of a synonym."""

        if stream_name not in constants.STREAM_SYNONYMS:
            return stream_name

        # if the name is a synonym, go through the streams
        for name, stream in streams.items():
            # See if we can find a better name
            if stream is streams[stream_name] and name not in constants.STREAM_SYNONYMS:
                return name

        return stream_name


    def output_stream(self, stream):
        """Open stream, create output and finally write the stream to output."""
        for i in range(self.args.retry_open):
            try:
                stream_fd, prebuffer = self.open_stream(stream)
                break
            except StreamError:
                # TODO: Log if you have to retry
                raise
        else:
            return

        if os.path.isfile(self.args.output) and not self.args.force:
            raise IOError("check_file_output in livestreamercli: File already exists!")

        out = output.FileOutput(self.args.output)
        out.open()

        try:
            with contextlib.closing(out):
                self.read_stream(stream_fd, out, prebuffer)
        finally:
            stream_fd.close()
        return True

    @staticmethod
    def open_stream(stream):
        """Opens a stream and reads 8192 bytes from it.

        This is useful to check if a stream actually has data
        before opening the output.

        returns connection to twitch
        """
        # Attempts to open the stream
        try:
            stream_fd = stream.open()
        except StreamError as err:
            raise StreamError("Could not open stream: "+str(err))

        # Read 8192 bytes before proceeding to check for errors.
        # This is to avoid opening the output unnecessarily.
        try:
            # TODO debug? "Pre-buffering 8192 bytes"
            prebuffer = stream_fd.read(8192)
        except IOError as err:
            raise StreamError("Failed to read data from stream: "+str(err))

        if not prebuffer:
            raise StreamError("No data returned from stream")

        return stream_fd, prebuffer

    @staticmethod
    def read_stream(stream, out, prebuffer, chunk_size=8192):
        """Reads data from stream and then writes it to the output."""

        stream_iterator = itertools.chain(
            [prebuffer],
            iter(functools.partial(stream.read, chunk_size), b"")
        )
        # TODO add some kind of a feedback object ref.
        stream_iterator = Progress(stream_iterator)

        try:
            for data in stream_iterator:
                try:
                    out.write(data)
                except IOError:
                    # TODO debug
                    raise
        except IOError:
            # TODO be nicer here?
            raise
        finally:
            stream.close()
