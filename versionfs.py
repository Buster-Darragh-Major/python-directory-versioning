#!/usr/bin/env python
from __future__ import with_statement

import logging

import os
import sys
import errno
import re

from fuse import FUSE, FuseOSError, Operations, LoggingMixIn

# Constant for max. number of version files
MAX_VER_COUNT = 6

# Finite state machine
state_dict = {
    'write': False,
    'flush': False,
}


class VersionFS(LoggingMixIn, Operations):
    def __init__(self):
        # get current working directory as place for versions tree
        self.root = os.path.join(os.getcwd(), '.versiondir')
        # check to see if the versions directory already exists
        if os.path.exists(self.root):
            print 'Version directory already exists.'
        else:
            print 'Creating version directory.'
            os.mkdir(self.root)

    # Helpers
    # =======

    def _full_path(self, partial):
        if partial.startswith("/"):
            partial = partial[1:]
        path = os.path.join(self.root, partial)
        return path

    def _copy_file(self, source, dest, buffer_size=1024*1024):
        with open(source, 'rb') as src, open(dest, 'wb') as dst:
            while True:
                copy_buffer = src.read(buffer_size)
                if not copy_buffer:
                    break
                dst.write(copy_buffer)

    # Acts as a FSM for determining whether a save should occur. This should only happen
    # under the order of write -> flush -> release
    def _is_save(self, state):
        if state == 'write':
            state_dict['write'] = True
            return False
        elif state_dict['write'] and state == 'flush':
            state_dict['flush'] = True
            return False
        elif state_dict['flush'] and state == 'release':
            state_dict['write'] = False
            state_dict['flush'] = False
            return True
        else:
            state_dict['write'] = False
            state_dict['flush'] = False
            return False

    # Filesystem methods
    # ==================

    def access(self, path, mode):
        # print "access:", path, mode
        full_path = self._full_path(path)
        if not os.access(full_path, mode):
            raise FuseOSError(errno.EACCES)

    def chmod(self, path, mode):
        # print "chmod:", path, mode
        full_path = self._full_path(path)
        return os.chmod(full_path, mode)

    def chown(self, path, uid, gid):
        # print "chown:", path, uid, gid
        full_path = self._full_path(path)
        return os.chown(full_path, uid, gid)

    def getattr(self, path, fh=None):
        # print "getattr:", path
        full_path = self._full_path(path)
        st = os.lstat(full_path)
        return dict((key, getattr(st, key)) for key in ('st_atime', 'st_ctime',
                     'st_gid', 'st_mode', 'st_mtime', 'st_nlink', 'st_size', 'st_uid'))

    # TODO: Modify this to only show non version files.
    def readdir(self, path, fh):
        # print "readdir:", path
        full_path = self._full_path(path)

        dirents = ['.', '..']
        if os.path.isdir(full_path):
            dirents.extend(os.listdir(full_path))
        for r in dirents:
            yield r

    def readlink(self, path):
        # print "readlink:", path
        pathname = os.readlink(self._full_path(path))
        if pathname.startswith("/"):
            # Path name is absolute, sanitize it.
            return os.path.relpath(pathname, self.root)
        else:
            return pathname

    def mknod(self, path, mode, dev):
        # print "mknod:", path, mode, dev
        return os.mknod(self._full_path(path), mode, dev)

    def rmdir(self, path):
        # print "rmdir:", path
        full_path = self._full_path(path)
        return os.rmdir(full_path)

    def mkdir(self, path, mode):
        # print "mkdir:", path, mode
        return os.mkdir(self._full_path(path), mode)

    def statfs(self, path):
        # print "statfs:", path
        full_path = self._full_path(path)
        stv = os.statvfs(full_path)
        return dict((key, getattr(stv, key)) for key in ('f_bavail', 'f_bfree',
            'f_blocks', 'f_bsize', 'f_favail', 'f_ffree', 'f_files', 'f_flag',
            'f_frsize', 'f_namemax'))

    def unlink(self, path):
        # print "unlink:", path
        return os.unlink(self._full_path(path))

    def symlink(self, name, target):
        # print "symlink:", name, target
        return os.symlink(target, self._full_path(name))

    def rename(self, old, new):
        # print "rename:", old, new
        return os.rename(self._full_path(old), self._full_path(new))

    def link(self, target, name):
        # print "link:", target, name
        return os.link(self._full_path(name), self._full_path(target))

    def utimens(self, path, times=None):
        # print "utimens:", path, times
        return os.utime(self._full_path(path), times)

    # File methods
    # ============

    def open(self, path, flags):
        print '** open:', path, '**'
        full_path = self._full_path(path)
        return os.open(full_path, flags)

    def create(self, path, mode, fi=None):
        print '** create:', path, '**'

        full_path = self._full_path(path)
        return os.open(full_path, os.O_WRONLY | os.O_CREAT, mode)

    def read(self, path, length, offset, fh):
        print '** read:', path, '**'
        os.lseek(fh, offset, os.SEEK_SET)
        return os.read(fh, length)

    def write(self, path, buf, offset, fh):
        print '** write:', path, '**'
        self._is_save('write')  # Tell FSM we have written
        os.lseek(fh, offset, os.SEEK_SET)
        return os.write(fh, buf)

    def truncate(self, path, length, fh=None):
        print '** truncate:', path, '**'
        full_path = self._full_path(path)
        with open(full_path, 'r+') as f:
            f.truncate(length)

    def flush(self, path, fh):
        print '** flush', path, '**'
        self._is_save('flush')  # Tell FSM we have flushed
        return os.fsync(fh)

    def release(self, path, fh):
        print '** release', path, '**'

        head, tail = os.path.split(path)  # Get filename of path and check whether it is hidden (starts with a '.')
        if self._is_save('release') and not tail.startswith('.'):
            min_version = -1
            max_version = 0
            no_versions = 0
            # Finding all files in directory
            for i in os.listdir(self.root):
                filename, ext = os.path.splitext(i)
                n = re.match("(\\S*)\\[\\d*\\]", filename)  # Get filename without any [...]
                if n:
                    filename = n.group(1)
                    m = re.match(filename + "\\[(\\d*)\\]" + ext + "?", i)
                    if m:
                        no_versions += 1
                        max_version = m.group(1) if max_version < m.group(1) else max_version
                        min_version = m.group(1) if (min_version < 0 or min_version > m.group(1)) else min_version

            if no_versions >= MAX_VER_COUNT:
                # Delete min-version
                filename, ext = os.path.splitext(path)
                to_delete = filename + '[' + min_version + ']' + ext
                os.remove(self.root + to_delete)

            name, ext = os.path.splitext(path)
            new_version = int(max_version) + 1
            to_create = name + '[' + str(new_version) + ']' + ext
            self._copy_file(self.root + path, self.root + to_create)
            print "COPIED"
            # TODO: This method copies the file BEFORE it has been saved :/

        return os.close(fh)

    def fsync(self, path, fdatasync, fh):
        print '** fsync:', path, '**'
        return self.flush(path, fh)


def main(mountpoint):
    FUSE(VersionFS(), mountpoint, nothreads=True, foreground=True)

if __name__ == '__main__':
    # logging.basicConfig(level=logging.DEBUG)
    main(sys.argv[1])