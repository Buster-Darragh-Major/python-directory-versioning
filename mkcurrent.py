#!/usr/bin/env python

import os
import re
import sys

MAX_VER_COUNT = 6

if __name__ == '__main__':

    # If user wants to restore version 1 it will be assumed no change takes place
    if sys.argv[2] is '1':
        exit(0)

    def _full_path(xroot, partial):
        if partial.startswith("/"):
            partial = partial[1:]
        path = os.path.join(xroot, partial)
        return path

    root = os.path.join(os.getcwd(), '.versiondir/versions')
    root_no_ver = os.path.join(os.getcwd(), '.versiondir')

    filename, ext = os.path.splitext(sys.argv[1])

    min_version = -1
    max_version = 0
    ver_count = 0
    version_list = []
    for i in os.listdir(root):
        m = re.match('.' + filename + '\\[(\\d*)\\]' + ext, i)
        if m:
            version_list.append(m.group(1))
            ver_count += 1
            max_version = int(m.group(1)) if max_version < int(m.group(1)) else max_version
            min_version = int(m.group(1)) if (min_version < 0 or min_version > int(m.group(1))) else min_version

    if len(version_list) < int(sys.argv[2]):
        print "You don't have that many versions."
        exit(1)

    version_list.sort(reverse=True)
    to_copy = _full_path(root, '.' + filename + '[' + version_list[int(sys.argv[2]) - 1] + ']' + ext)
    latest_version = _full_path(root, '.' + filename + '[' + str(max_version + 1) + ']' + ext)

    with open(to_copy, 'rb') as src, \
            open(_full_path(root_no_ver, sys.argv[1]), 'wb') as dst, \
            open(latest_version, 'wb') as new:
        while True:
            copy_buffer = src.read(1024*1024)
            if not copy_buffer:
                break
            dst.write(copy_buffer)
            new.write(copy_buffer)

    if ver_count >= MAX_VER_COUNT:
        # Delete min-version
        to_delete = '.' + filename + '[' + str(min_version) + ']' + ext
        os.remove(_full_path(root, to_delete))
