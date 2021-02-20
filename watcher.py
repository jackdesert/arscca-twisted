"""
This module is used to observe files and notify on changes
"""
from datetime import datetime
from datetime import timedelta
from pwd import getpwuid
from shutil import copyfile
import os

from twisted.internet import inotify
from twisted.python.filepath import FilePath


# pylint: disable=too-few-public-methods
class Watcher:
    """
    Adapted from
    https://twistedmatrix.com/documents/current/api/twisted.internet.inotify.html
    """

    class FileMissing(Exception):
        """WATCHED_FILENAME does not exist on disk"""

    class FileOwnershipError(Exception):
        """Expected WATCHED_FILENAME to be owned by particular user"""

    UPDATE = 2
    ATTRIB = 4
    DELETE_SELF = 1024

    DUPLICATE_WINDOW_MILLISECONDS = 50
    FILE_POPULATION_DELAY_SECONDS = 0.020  # Must be more than 0.002
    CONNECTION_LOST_DELAY_SECONDS = 1  # How long to wait before removing file handle

    WATCHED_FILENAME = '/home/arscca/arscca-live.jinja2'
    WATCHED_FILENAME_OBJECT = FilePath(WATCHED_FILENAME.encode())
    ARCHIVE_DIR = '/home/arscca/archive'
    EXPECTED_OWNER_OF_WATCHED_FILE = 'arscca'
    EXPECTED_GROUP_OF_ARCHIVE_DIR = 'www-data'

    __slots__ = ('callback', '_recent_update', '_notifier')

    def __init__(self, callback):
        self.callback = callback
        self._ensure_correct_ownership()
        self._recent_update = datetime.now()
        self._notifier = None  # To be written later

    def watch(self):
        """
        Watch the file and set a callback
        """
        notifier = inotify.INotify()
        notifier.startReading()
        notifier.watch(self.WATCHED_FILENAME_OBJECT, callbacks=[self._invoke_callback])
        self._notifier = notifier

    # pylint: disable=unused-argument
    def _invoke_callback(self, ignored, filepath, mask):
        mask_h = inotify.humanReadableMask(mask)

        # meta updating file via vim shows up as UPDATE, and triggers
        # sometimes only once, and sometimes TWICE :/ (See inotify docs
        # on coalesced events)
        # meta updating file via `echo ' ' >> FILE` shows up as UPDATE
        # meta updating file via rsync shows up as ATTRIB, then DELETE_SELF
        if mask == self.UPDATE:
            # When file is updated via linux `cp`,
            # Sometimes UPDATE happens twice about 2 milliseconds apart.
            # (And the file is still empty when the first one hits)
            # Other times those two events are coalesced into one
            # (See inotify man page regarding coalesced events)
            # THEREFORE we trigger on only the first within a time window,
            # BUT we also insert a small delay to give the file
            # time to actually be populated.
            now = datetime.now()
            delta = now - self._recent_update
            self._recent_update = now
            delta_seconds = delta.seconds + delta.microseconds / 1e6
            action = (
                f'Callback skipped because duplicate. delta_seconds: {delta_seconds}'
            )

            # Rate limit this event by only allowing the first of events in a window
            if delta > timedelta(milliseconds=self.DUPLICATE_WINDOW_MILLISECONDS):
                action = f'Callback will be invoked in {self.FILE_POPULATION_DELAY_SECONDS}s.'
                # pylint: disable=redefined-outer-name,import-outside-toplevel
                from twisted.internet import reactor

                # pylint: disable=no-member
                # Call it enough in the future that the file is actually there
                reactor.callLater(self.FILE_POPULATION_DELAY_SECONDS, self.callback)

        if mask == self.ATTRIB:
            # When file is updated (remotely) via rsync , we end up here
            msg = self._archive_file()
            action = f'{msg}Callback invoked now.'
            self.callback()

        if mask == self.DELETE_SELF:
            # For some reason when updating the file via rsync (remotely)
            # DELETE_SELF is triggered, which causes the file to no longer be watched

            # Tell it to delete the file descriptor (connectionLost).
            # Otherwise we eventually run out of file descriptors
            # Note we do this in the future, because if we call it inline (now),
            # our process stops watching the file.
            action = 'restarted file watcher'
            # pylint: disable=import-outside-toplevel
            from twisted.internet import reactor

            # pylint: disable=no-member
            reactor.callLater(
                self.CONNECTION_LOST_DELAY_SECONDS,
                self._notifier.connectionLost,
                'rsync issued DELETE_SELF',
            )
            # Start Over
            self.watch()

        print(f'MASK: {mask_h}, action: {action}')

    def _ensure_correct_ownership(self):
        # Make sure file is present
        # BECAUSE if file does not exist, arscca-pyramid will throw an error
        assert os.path.isfile(self.WATCHED_FILENAME)

        # Make sure file is owned by correct owner
        # BECAUSE rsync needs to be able to write to it.
        # (Commented out to run under Docker
        #  because docker and host do not share the same user ids)
        # assert self._owner_of_watched_file == self.EXPECTED_OWNER_OF_WATCHED_FILE

        # Make sure file can be read by this process
        assert os.access(self.WATCHED_FILENAME, os.R_OK)

        # Make sure archive dir is owned by the correct owner
        # Otherwise this process will not be able to write files there
        # (Commented out to run under Docker
        #  because docker and host do not share the same user ids)
        # assert self._group_of_archive_dir  == self.EXPECTED_GROUP_OF_ARCHIVE_DIR

        # Make sure directory is writable by this process
        assert os.access(self.ARCHIVE_DIR, os.W_OK)

    def _archive_file(self):
        # It only makes sense to call this when running via rsync (actual events)
        # Because if you call this for demo_cp, it fills up the disk
        now = datetime.now()
        now_string = now.strftime('%Y-%m-%d--%H%M%S.%f')
        dest = f'{self.ARCHIVE_DIR}/{now_string}.jinja2'
        copyfile(self.WATCHED_FILENAME, dest)
        return f'File copied to {dest}. '

    # pylint: disable=line-too-long
    @property
    def _owner_of_watched_file(self):
        """
        See https://stackoverflow.com/questions/1830618/how-to-find-the-owner-of-a-file-or-directory-in-python
        """
        uid = os.stat(self.WATCHED_FILENAME).st_uid
        return getpwuid(uid).pw_name

    @property
    def _group_of_archive_dir(self):
        """
        See https://stackoverflow.com/questions/1830618/how-to-find-the-owner-of-a-file-or-directory-in-python
        """
        gid = os.stat(self.ARCHIVE_DIR).st_gid
        return getpwuid(gid).pw_name


if __name__ == '__main__':

    def my_callback():
        """
        A simple callback for demonstration purposes
        """
        print('Inside Callback')

    watcher = Watcher(my_callback)
    watcher.watch()

    # At some point you must start a reactor
    # pylint: disable=redefined-outer-name
    from twisted.internet import reactor

    # pylint: disable=no-member
    reactor.run()
