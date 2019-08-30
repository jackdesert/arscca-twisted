from datetime import datetime
from shutil import copyfile
from twisted.internet import inotify
from twisted.python.filepath import FilePath
import os
import pdb

class Watcher:
    # Adapted from
    # https://twistedmatrix.com/documents/current/api/twisted.internet.inotify.html

    UPDATE = 2
    WATCHED_FILENAME = '/tmp/arscca-live.jinja2'
    WATCHED_FILENAME_OBJECT = FilePath(WATCHED_FILENAME.encode())

    def __init__(self, callback):
        self.callback = callback
        self._ensure_watched_filename_exists()

    def watch(self):
        notifier = inotify.INotify()
        notifier.startReading()
        notifier.watch(self.WATCHED_FILENAME_OBJECT, callbacks=[self._invoke_callback])

    def _invoke_callback(self, ignored, filepath, mask):
        # Note you will end up in this method TWICE
        # if you change the file and save from Vim
        if mask == self.UPDATE:
            archive_file_name = self._archive_file()
            print(f'file copied to {archive_file_name}. Callback invoked.')
            self.callback()

    def _ensure_watched_filename_exists(self):
        if os.path.isfile(self.WATCHED_FILENAME):
            return
        with open(self.WATCHED_FILENAME, 'w', encoding='utf-8') as f:
            f.write('<h1>Waiting for AxWare file to be uploaded</h1>')

    def _archive_file(self):
        now = datetime.now()
        now_string = now.strftime('%Y-%m-%d--%H%M%S.%f')
        dest = f'.archive/{now_string}.jinja2'
        copyfile(self.WATCHED_FILENAME, dest)
        return dest



if __name__ == '__main__':

    def my_callback():
        print('Inside Callback')

    watcher = Watcher(my_callback)
    watcher.watch()
    from twisted.internet import reactor

    # At some point you must start a reactor
    reactor.run()

