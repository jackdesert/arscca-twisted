from datetime import datetime
from datetime import timedelta
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
    DELETE_SELF = 1024

    WATCHED_FILENAME = '/home/arscca/arscca-live.jinja2'
    WATCHED_FILENAME_OBJECT = FilePath(WATCHED_FILENAME.encode())
    ARCHIVE_DIR = '/home/arscca/archive'
    EXPECTED_OWNER_OF_WATCHED_FILE = 'arscca'
    EXPECTED_GROUP_OF_ARCHIVE_DIR = 'www-data'

    def __init__(self, callback):
        self.callback = callback
        self._ensure_correct_ownership()
        self._recent_update = datetime.now()

    def watch(self):
        notifier = inotify.INotify()
        notifier.startReading()
        notifier.watch(self.WATCHED_FILENAME_OBJECT, callbacks=[self._invoke_callback])
        self._notifier = notifier

    def _invoke_callback(self, ignored, filepath, mask):
        mask_h = inotify.humanReadableMask(mask)
        archive_file_name = self._archive_file()
        print(f'MASK: {mask_h}')

        # Note updating file via vim shows up as UPDATE, and triggers TWICE :/
        # Note updating file via `echo ' ' >> FILE` shows up as UPDATE
        # Note updating file via rsync shows up as ATTRIB, then DELETE_SELF
        if mask == self.UPDATE:
            # When file is updated via linux `cp`, UPDATE happens twice
            # about 2 milliseconds apart.
            # We call the callback on the second one
            # because otherwise arscca-pyramid will end up reading a blank file
            now = datetime.now()
            delta = now - self._recent_update 
            self._recent_update = now
            if delta < timedelta(milliseconds=50):
                print(f'file copied to {archive_file_name}. Callback invoked now.')
                self.callback()

        if mask == self.ATTRIB:
            # When file is updated (remotely) via rsync , we end up here
            print(f'file copied to {archive_file_name}. Callback invoked now.')
            self.callback()

        if mask == self.DELETE_SELF:
            # For some reason when updating the file via rsync (from remote)
            # DELETE_SELF is triggered, which causes the file to no longer be watched
            # Therefore we start over

            # Tell it to delete the file descriptor (connectionLost).
            # Otherwise we eventually run out of file descriptors
            # Note we do this in the future, because if we call it inline (now),
            # our process stops watching the file.
            from twisted.internet import reactor
            reactor.callLater(1, self._notifier.connectionLost, 'rsync issued DELETE_SELF')
            self.watch()

    def _ensure_correct_ownership(self):
        # Make sure file is present
        # BECAUSE if file does not exist, arscca-pyramid will throw an error
        assert os.path.isfile(self.WATCHED_FILENAME)

        # Make sure file is owned by correct owner
        # BECAUSE rsync needs to be able to write to it.
        assert self._owner_of_watched_file == self.EXPECTED_OWNER_OF_WATCHED_FILE
        # Make sure file can be read by this process
        assert os.access(self.WATCHED_FILENAME, os.R_OK)

        # Make sure archive dir is owned by the correct owner
        # Otherwise this process will not be able to write files there
        assert self._group_of_archive_dir  == self.EXPECTED_GROUP_OF_ARCHIVE_DIR
        # Make sure directory is writable by this process
        assert os.access(self.ARCHIVE_DIR, os.W_OK)


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

