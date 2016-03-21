import spotify
import threading
import subprocess
from MusicPlayer.queue import *


class AbstractPlayer(object):

    def __init__(self, end_of_track_callback):
        self.end_of_track_callback = end_of_track_callback
        print("calling parent constructor")

    def play_queue_item(self, QueueItem):
        raise NotImplementedError

    def skip_song(self):
        raise NotImplementedError

    def on_end_of_track(self):
        self.end_of_track_callback()


class SpotifyPlayer(AbstractPlayer):

    def __init__(self, username, password, end_of_track_callback):
        super().__init__(end_of_track_callback)

        self.session = spotify.Session()
        print("logging into spotify")

        self.session.login(username, password, True)

        loop = spotify.EventLoop(self.session)
        loop.start()

        self.logged_in = threading.Event()

        self.audio = spotify.AlsaSink(self.session)

        self.session.on(spotify.SessionEvent.CONNECTION_STATE_UPDATED, self.on_connection_state_updated)
        self.session.on(spotify.SessionEvent.END_OF_TRACK, self.on_end_of_spotify_track)
        self.session.on(spotify.SessionEvent.PLAY_TOKEN_LOST, self.on_end_of_spotify_track)

        self.logged_in.wait()

    def on_connection_state_updated(self, session):
        if session.connection.state is spotify.ConnectionState.LOGGED_IN:
            self.logged_in.set()
        else:
            print(session.connection.state)

    def play_queue_item(self, QueueItem):
        url = QueueItem.get_url()
        track = self.session.get_track(url).load()
        self.session.player.load(track)
        self.session.player.play()

    def on_end_of_spotify_track(self, session):
        self.session.player.pause()
        self.on_end_of_track()

    def skip_song(self):
        self.session.player.unload()
        self.on_end_of_track()


class YoutubePlayer(AbstractPlayer):

    def __init__(self, end_of_track_callback):
        super().__init__(end_of_track_callback)
        self.thread = None
        self.subProcess = None

    def play_url(self, callback, url):
        """
        Runs the given args in a subprocess.Popen, and then calls the function
        onExit when the subprocess completes.
        onExit is a callable object, and popenArgs is a list/tuple of args that
        would give to subprocess.Popen.
        """
        def runInThread(callback, url):
            proc = subprocess.Popen(['/usr/bin/mpv', url, '--no-video'], stdin=subprocess.PIPE)
            self.subProcess = proc
            proc.wait()
            callback()
            return

        thread = threading.Thread(target=runInThread, args=(callback, url))
        thread.start()
        self.thread = thread
        return thread

    def play_queue_item(self, QueueItem):
        url = QueueItem.get_url()
        print("YOUTUBE URL: " + url)
        self.play_url(self.on_end_of_track, url)

    def skip_song(self):
        print("trying to skip a youtube song")
        if self.thread is not None and self.thread.is_alive():
            print("printing q to mpv")
            self.subProcess.kill()


class MusicPlayer(object):

    def __init__(self, options):

        if 'spotify_username' in options:
            self.spotify_player = SpotifyPlayer(options.get('spotify_username'), options.get('spotify_password'), self.on_end_of_track)
        else:
            print("Spotify support disabled")
            self.spotify_player = None
        self.youtube_player = YoutubePlayer(self.on_end_of_track)
        self.queue = Queue()
        self.current = None
        self.current_player = None
        self.shouldStop = threading.Event()
        self.hasStarted = False

    def start(self):
        self.play_next()
        self.hasStarted = True

    def play_next(self):
        if self.queue.has_next():
            item = self.queue.get_next()
            self.current = item
            if isinstance(item, SpotifyQueueItem):
                print("song is a spotifysong")
                if self.spotify_player is None:
                    raise Exception('Spotify support is not enabled')
                self.current_player = self.spotify_player
                self.spotify_player.play_queue_item(item)
            elif isinstance(item, YoutubeQueueItem):
                print("song is a youtube song")
                self.current_player = self.youtube_player
                self.youtube_player.play_queue_item(item)

    def skip_song(self):
        if self.is_playing():
            self.current_player.skip_song()

    def get_queue_string(self):
        res = ""
        for item in self.queue.get_all():
            res += item.get_url() + "\r\n"

        return res

    def is_playing(self):
        return self.current is not None

    def add_to_queue(self, queue_item):
        """
        :param QueueItem QueueItem:
        """
        self.queue.add(queue_item)
        if self.hasStarted and not self.is_playing():
            self.play_next()

    def on_end_of_track(self):
        print("A TRACK HAS ENDED")
        self.current = None
        self.current_player = None
        if self.queue.has_next():
            self.play_next()
        else:
            self.shouldStop.set()
