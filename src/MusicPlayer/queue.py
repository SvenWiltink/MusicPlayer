class Queue(object):

    def __init__(self):
        self.queue_items = []

    def add(self, item):
        self.queue_items.append(item)

    def get_next(self):
        """
        :rtype: QueueItem
        """
        return self.queue_items.pop(0)

    def has_next(self):
        return len(self.queue_items) > 0


class QueueItem(object):

    def __init__(self, url):
        self.url = url

    def get_url(self):
        return self.url


class SpotifyQueueItem(QueueItem):
    pass


class YoutubeQueueItem(QueueItem):
    pass
