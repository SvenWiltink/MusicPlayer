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

    def stop(self):
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
        self.on_end_of_track()
        self.session.player.pause()

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
            proc = subprocess.Popen(['mpsyt', "playurl", url], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            proc.wait()
            print("PROC WAIT ENDED")
            callback()
            return

        thread = threading.Thread(target=runInThread, args=(callback, url))
        thread.start()
        return thread

    def play_queue_item(self, QueueItem):
        url = QueueItem.get_url()
        print("YOUTUBE URL: " + url)
        self.play_url(self.on_end_of_track, url)

    def stop(self):
        if self.thread is not None and self.thread.is_alive():
            self.subProcess.communicate(input='q')


class MusicPlayer(object):

    def __init__(self, spotify_username, spotify_password):
        self.spotify_player = SpotifyPlayer(spotify_username, spotify_password, self.on_end_of_track)
        self.youtube_player = YoutubePlayer(self.on_end_of_track)
        self.queue = Queue()
        self.current = None
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
                self.spotify_player.play_queue_item(item)
            elif isinstance(item, YoutubeQueueItem):
                print("song is a youtube song")
                self.youtube_player.play_queue_item(item)

    def is_playing(self):
        return self.current is not None

    def add_to_queue(self, QueueItem):
        """
        :param QueueItem QueueItem:
        """
        self.queue.add(QueueItem)
        if self.hasStarted and not self.is_playing():
            self.play_next()

    def on_end_of_track(self):
        print("A TRACK HAS ENDED")
        if self.queue.has_next():
            self.play_next()
        else:
            self.shouldStop.set()
