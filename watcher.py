from twisted.internet import inotify
from twisted.python.filepath import FilePath
import pdb

class Watcher:
    # At some point you must start a reactor

    UPDATE = 2
    WATCHED_FILENAME = FilePath(b'/tmp/arscca-live.jinja2')


    def __init__(self, callback):
        self.callback = callback

    def watch(self):
        notifier = inotify.INotify()
        notifier.startReading()
        notifier.watch(self.WATCHED_FILENAME, callbacks=[self._invoke_callback])

    def _invoke_callback(self, ignored, filepath, mask):
        if mask == self.UPDATE:
            print(f'file updated: {filepath}. Invoking callback {self.callback}')
            self.callback()


if __name__ == '__main__':

    def my_callback():
        print('Inside Callback')

    watcher = Watcher(my_callback)
    watcher.watch()
    from twisted.internet import reactor
    reactor.run()

