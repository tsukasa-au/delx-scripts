#!/usr/bin/python3

from __future__ import division

import os
import sys

def pp_size(size):
    suffixes = ["", "KiB", "MiB", "GiB"]
    for i, suffix in enumerate(suffixes):
        if size < 1024:
            break
        size /= 1024
    return "%.2f %s" % (size, suffix)


def check_path(path):
    stat = os.statvfs(path)
    total = stat.f_bsize * stat.f_blocks
    free = stat.f_bsize * stat.f_bavail
    warn = False

    if total < 5*1024*1024*1024:
        if free < total * 0.05:
            warn = True
    elif free < 2*1024*1024*1024:
        warn = True

    if warn:
        print("WARNING! %s has only %s remaining" % (path, pp_size(free)))


def main():
    paths = sys.argv[1:]
    if not paths:
        print("Usage: %s path" % sys.argv[0])
        sys.exit(1)
    for path in paths:
        check_path(path)

if __name__ == "__main__":
    main()

