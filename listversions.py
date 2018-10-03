
# TODO: remove extension on this file
# TODO: Insert shebang

import sys
import os
import re

if __name__ == '__main__':
    root = os.path.join(os.getcwd(), '.versiondir')
    for i in os.listdir(root):
        m = re.match("\\S*\\[\\d*\\](\\.\\S*)?$", sys.argv[1])
        