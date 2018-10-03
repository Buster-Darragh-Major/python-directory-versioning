
# TODO: remove extension on this file
# TODO: Insert shebang

import sys
import os
import re

if __name__ == '__main__':
    root = os.path.join(os.getcwd(), '.versiondir')

    version_count = 0
    for i in os.listdir(root):
        filename, ext = os.path.splitext(sys.argv[1])
        m = re.match('.' + filename + "\[(\d*)\]" + ext + "$", i)
        if m:
            version_count += 1

    for i in xrange(version_count):
        print sys.argv[1] + '.' + str(i + 1)