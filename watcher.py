from datetime import datetime
from shutil import copyfile

# Utilites for ascertaining owner and group of files
from pwd import getpwuid

from twisted.internet import inotify
from twisted.python.filepath import FilePath

import os
import pdb

class Watcher:
    # Adapted from
    # https://twistedmatrix.com/documents/current/api/twisted.internet.inotify.html

    class FileMissing(Exception):
        '''WATCHED_FILENAME does not exist on disk'''

    class FileOwnershipError(Exception):
       '''Expected WATCHED_FILENAME to be owned by particular user'''

    UPDATE = 2
    ATTRIB = 4
    WATCHED_FILENAME = '/home/arscca/arscca-live.jinja2'
    WATCHED_FILENAME_OBJECT = FilePath(WATCHED_FILENAME.encode())
    ARCHIVE_DIR = '/home/arscca/archive'
    EXPECTED_OWNER_OF_WATCHED_FILE = 'arscca'
    EXPECTED_GROUP_OF_ARCHIVE_DIR = 'www-data'

    def __init__(self, callback):
        self.callback = callback
        self._ensure_correct_ownership()

    def watch(self):
        notifier = inotify.INotify()
        notifier.startReading()
        notifier.watch(self.WATCHED_FILENAME_OBJECT, callbacks=[self._invoke_callback])

    def _invoke_callback(self, ignored, filepath, mask):
        #mask_h = inotify.humanReadableMask(mask)
        
        # Note updating file via vim shows up as UPDATE, and triggers TWICE :/
        # Note updating file via `echo ' ' >> FILE` shows up as UPDATE
        # Note updating file via rsync shows up as ATTRIB, then DELETE_SELF
        if mask in (self.UPDATE, self.ATTRIB):
            archive_file_name = self._archive_file()
            print(f'file copied to {archive_file_name}. Callback invoked.')
            self.callback()

    def _ensure_correct_ownership(self):
        # Make sure file is present 
        # BECAUSE if file does not exist, arscca-pyramid will throw an error
        assert os.path.isfile(self.WATCHED_FILENAME)

        # Make sure file is owned by correct owner
        # BECAUSE rsync needs to be able to write to it. 
        assert self._owner_of_watched_file == self.EXPECTED_OWNER_OF_WATCHED_FILE

        # Make sure archive dir is owned by the correct owner
        # Otherwise this process will not be able to write files there
        assert self._group_of_archive_dir  == self.EXPECTED_GROUP_OF_ARCHIVE_DIR


    def _archive_file(self):
        now = datetime.now()
        now_string = now.strftime('%Y-%m-%d--%H%M%S.%f')
        dest = f'{self.ARCHIVE_DIR}/{now_string}.jinja2'
        copyfile(self.WATCHED_FILENAME, dest)
        return dest

    @property
    def _owner_of_watched_file(self):
        # See https://stackoverflow.com/questions/1830618/how-to-find-the-owner-of-a-file-or-directory-in-python
        uid = os.stat(self.WATCHED_FILENAME).st_uid
        return getpwuid(uid).pw_name

    @property
    def _group_of_archive_dir(self):
        # See https://stackoverflow.com/questions/1830618/how-to-find-the-owner-of-a-file-or-directory-in-python
        gid = os.stat(self.ARCHIVE_DIR).st_gid
        return getpwuid(gid).pw_name


if __name__ == '__main__':

    def my_callback():
        print('Inside Callback')

    watcher = Watcher(my_callback)
    watcher.watch()
    from twisted.internet import reactor

    # At some point you must start a reactor
    reactor.run()

