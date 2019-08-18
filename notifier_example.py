from twisted.internet import inotify
from twisted.python.filepath import FilePath
import pdb

UPDATE = 2
WATCHED_FILENAME = FilePath(b'/tmp/arscca-live.jinja2')

def notify_on_update(ignored, filepath, mask):
    if mask == UPDATE and filepath == WATCHED_FILENAME:
        print(f'file updated: {filepath}')

notifier = inotify.INotify()
notifier.startReading()
notifier.watch(FilePath("/tmp"), callbacks=[notify_on_update])

from twisted.internet import reactor
reactor.run()
