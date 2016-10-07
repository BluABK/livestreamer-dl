import os
import signal

import contextlib
import functools
import itertools
import time
import collections

from livestreamer import (Livestreamer, StreamError, PluginError, NoPluginError)

import livestreamer_cli.argparser as argparser
import livestreamer_cli.constants as constants
import livestreamer_cli.output as output


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

args = livestreamer = None


def create_output():
    """Checks if file already exists and ask the user if it should
    be overwritten if it does."""

    if os.path.isfile(args.output) and not args.force:
        raise IOError("check_file_output in livestreamercli: File already exists!")

    return output.FileOutput(args.output)


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


def output_stream(stream):
    """Open stream, create output and finally write the stream to output."""
    for i in range(args.retry_open):
        try:
            stream_fd, prebuffer = open_stream(stream)
            break
        except StreamError:
            # TODO: Log if you have to retry
            raise
    else:
        return

    out = create_output()

    try:
        out.open()
    except (IOError, OSError):
        raise

    try:
        with contextlib.closing(out):
            read_stream(stream_fd, out, prebuffer)
    finally:
        stream_fd.close()

    return True


def read_stream(stream, out, prebuffer, chunk_size=8192):
    """Reads data from stream and then writes it to the output."""

    stream_iterator = itertools.chain(
        [prebuffer],
        iter(functools.partial(stream.read, chunk_size), b"")
    )
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


def handle_stream(streams, stream_name):
    """Decides what to do with the selected stream.

    Depending on arguments it can be one of these:
     - Output internal command-line
     - Output JSON represenation
     - Continuously output the stream over HTTP
     - Output stream data to selected output

    """

    stream_names = [resolve_stream_name(streams, stream_name)]

    # Find any streams with a '_alt' suffix and attempt to use these in case the main stream is not usable.
    if stream_name + "_alt" in streams.keys():
        stream_names += stream_name + "_alt"

    for stream_name in stream_names:
        if output_stream(streams[stream_name]):
            break


def fetch_streams(plugin):
    """Attempts to fetch streams until some are returned.
        args.retry_streams - seconds between each attempt
    """

    try:
        streams = plugin.get_streams(stream_types=args.stream_types,
                                     sorting_excludes=args.stream_sorting_excludes)
    except PluginError:
        # TODO: This is what happens when we cannot start streaming right away
        raise

    if not streams and not args.retry_streams:
        return None

    while not streams:
        time.sleep(args.retry_streams)

        try:
            streams = plugin.get_streams(stream_types=args.stream_types,
                                         sorting_excludes=args.stream_sorting_excludes)
        except PluginError:
            # TODO: This is what happens for every failed retry
            pass

    return streams


def resolve_stream_name(streams, stream_name):
    """Returns the real stream name of a synonym."""

    if stream_name in constants.STREAM_SYNONYMS and stream_name in streams:
        for name, stream in streams.items():
            if stream is streams[stream_name] and name not in constants.STREAM_SYNONYMS:
                return name

    return stream_name


def format_valid_streams(streams):
    """Formats a dict of streams.

    Filters out synonyms and displays them next to
    the stream they point to.

    """

    delimiter = ", "
    validstreams = []

    for name, stream in sorted(streams.items()):
        if name in constants.STREAM_SYNONYMS:
            continue

        synonyms = list(filter(lambda n: stream is streams[n] and n is not name, streams.keys()))

        if len(synonyms) > 0:
            name += " (%s)" % delimiter.join(synonyms)

        validstreams.append(name)

    return delimiter.join(validstreams)


def handle_url():
    """The URL handler.

    Attempts to resolve the URL to a plugin and then attempts
    to fetch a list of available streams.

    Proceeds to handle stream if user specified a valid one,
    otherwise output list of valid streams.

    """

    try:
        streams = fetch_streams(livestreamer.resolve_url(args.url))
    except NoPluginError:
        raise
    except PluginError:
        raise

    if not streams:
        raise Exception("No streams found on this URL: " + args.url)

    for stream_name in args.stream:
        if stream_name in streams:
            handle_stream(streams, stream_name)
            return

    raise Exception("The specified stream(s) '%s' could not be found" % ", ".join(args.stream))


def setup_http_session():
    """Sets the global HTTP settings, such as proxy and headers."""
    if args.http_proxy:
        livestreamer.set_option("http-proxy", args.http_proxy)

    if args.https_proxy:
        livestreamer.set_option("https-proxy", args.https_proxy)

    if args.http_cookie:
        livestreamer.set_option("http-cookies", dict(args.http_cookie))

    if args.http_header:
        livestreamer.set_option("http-headers", dict(args.http_header))

    if args.http_query_param:
        livestreamer.set_option("http-query-params", dict(args.http_query_param))

    if args.http_ignore_env:
        livestreamer.set_option("http-trust-env", False)

    if args.http_no_ssl_verify:
        livestreamer.set_option("http-ssl-verify", False)

    if args.http_ssl_cert:
        livestreamer.set_option("http-ssl-cert", args.http_ssl_cert)

    if args.http_ssl_cert_crt_key:
        livestreamer.set_option("http-ssl-cert", tuple(args.http_ssl_cert_crt_key))

    if args.http_timeout:
        livestreamer.set_option("http-timeout", args.http_timeout)


def setup_options():
    """Sets Livestreamer options."""
    if args.hls_live_edge:
        livestreamer.set_option("hls-live-edge", args.hls_live_edge)

    if args.hls_segment_attempts:
        livestreamer.set_option("hls-segment-attempts", args.hls_segment_attempts)

    if args.hls_segment_threads:
        livestreamer.set_option("hls-segment-threads", args.hls_segment_threads)

    if args.hls_segment_timeout:
        livestreamer.set_option("hls-segment-timeout", args.hls_segment_timeout)

    if args.hls_timeout:
        livestreamer.set_option("hls-timeout", args.hls_timeout)

    if args.hds_live_edge:
        livestreamer.set_option("hds-live-edge", args.hds_live_edge)

    if args.hds_segment_attempts:
        livestreamer.set_option("hds-segment-attempts", args.hds_segment_attempts)

    if args.hds_segment_threads:
        livestreamer.set_option("hds-segment-threads", args.hds_segment_threads)

    if args.hds_segment_timeout:
        livestreamer.set_option("hds-segment-timeout", args.hds_segment_timeout)

    if args.hds_timeout:
        livestreamer.set_option("hds-timeout", args.hds_timeout)

    if args.http_stream_timeout:
        livestreamer.set_option("http-stream-timeout", args.http_stream_timeout)

    if args.ringbuffer_size:
        livestreamer.set_option("ringbuffer-size", args.ringbuffer_size)

    if args.rtmp_proxy:
        livestreamer.set_option("rtmp-proxy", args.rtmp_proxy)

    if args.rtmp_rtmpdump:
        livestreamer.set_option("rtmp-rtmpdump", args.rtmp_rtmpdump)

    if args.rtmp_timeout:
        livestreamer.set_option("rtmp-timeout", args.rtmp_timeout)

    if args.stream_segment_attempts:
        livestreamer.set_option("stream-segment-attempts", args.stream_segment_attempts)

    if args.stream_segment_threads:
        livestreamer.set_option("stream-segment-threads", args.stream_segment_threads)

    if args.stream_segment_timeout:
        livestreamer.set_option("stream-segment-timeout", args.stream_segment_timeout)

    if args.stream_timeout:
        livestreamer.set_option("stream-timeout", args.stream_timeout)

    livestreamer.set_option("subprocess-errorlog", args.subprocess_errorlog)


def setup_plugin_options():
    """Sets Livestreamer plugin options."""
    if args.twitch_cookie:
        livestreamer.set_plugin_option("twitch", "cookie", args.twitch_cookie)

    if args.twitch_oauth_token:
        livestreamer.set_plugin_option("twitch", "oauth_token",
                                       args.twitch_oauth_token)

    if args.ustream_password:
        livestreamer.set_plugin_option("ustreamtv", "password",
                                       args.ustream_password)

    if args.crunchyroll_username:
        livestreamer.set_plugin_option("crunchyroll", "username",
                                       args.crunchyroll_username)

    if args.crunchyroll_password:
        livestreamer.set_plugin_option("crunchyroll", "password",
                                       args.crunchyroll_password)

    if args.crunchyroll_purge_credentials:
        livestreamer.set_plugin_option("crunchyroll", "purge_credentials",
                                       args.crunchyroll_purge_credentials)

    if args.livestation_email:
        livestreamer.set_plugin_option("livestation", "email",
                                       args.livestation_email)

    if args.livestation_password:
        livestreamer.set_plugin_option("livestation", "password",
                                       args.livestation_password)


def main(output_arg, url_arg, quality_arg):
    global args
    global livestreamer

    args = argparser.parser.parse_args(['-o', output_arg, url_arg, quality_arg])

    livestreamer = Livestreamer()

    if os.path.isdir(constants.PLUGINS_DIR):
        livestreamer.load_plugins(os.path.expanduser(constants.PLUGINS_DIR))

    # === config files
    config_files = []

    try:
        config_files += [fn+"."+livestreamer.resolve_url(args.url).module for fn in constants.CONFIG_FILES]
    except NoPluginError:
        pass

    # Only load first available default config
    for config_file in filter(os.path.isfile, constants.CONFIG_FILES):
        config_files.append(config_file)
        break

    if config_files:
        """Parses arguments."""
        arglist = []
        # Load arguments from config files
        for config_file in filter(os.path.isfile, reversed(config_files)):
            arglist.append("@" + config_file)

        arglist += ['-o', output_arg, url_arg, quality_arg]

        args = argparser.parser.parse_args(arglist)

    # Handle SIGTERM just like SIGINT
    signal.signal(signal.SIGTERM, signal.default_int_handler)

    setup_http_session()
    setup_options()
    setup_plugin_options()
    handle_url()
