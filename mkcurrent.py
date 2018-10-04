#!/usr/bin/env python

import os
import re
import sys

if __name__ == '__main__':

    def _full_path(xroot, partial):
        if partial.startswith("/"):
            partial = partial[1:]
        path = os.path.join(xroot, partial)
        return path

    root = os.path.join(os.getcwd(), '.versiondir/versions')

    filename, ext = os.path.splitext(sys.argv[1])

    version_list = []
    for i in os.listdir(root):
        m = re.match('.' + filename + '\\[(\\d*)\\]' + ext, i)
        if m:
            version_list.append(m.group(1))

    if len(version_list) < int(sys.argv[2]):
        print "You don't have that many versions."
        exit(0)

    version_list.sort(reverse=True)
    to_copy = _full_path(root, '.' + filename + '[' + version_list[int(sys.argv[2]) - 1] + ']' + ext)

    with open(to_copy, 'rb') as src, open(_full_path(root, sys.argv[1]), 'wb') as dst:
        while True:
            copy_buffer = src.read(1024*1024)
            if not copy_buffer:
                break
            dst.write(copy_buffer)

