#!/usr/bin/env python2

# This tool tries to parse the weird hardlink format Apple uses for Time Machine
# The goal is to recover data from a Time Machine backup without a Mac

import math
import stat
import os
import sys

def find_lookup_dir(path):
    while path != "/":
        lookup_dir = os.path.join(path, ".HFS+ Private Directory Data\r")
        if os.path.isdir(lookup_dir):
            return lookup_dir
        path = os.path.split(path)[0]
    raise Exception("Could not find HFS+ link dir")

def resolve_path(lookup_dir, path):
    st = os.lstat(path)
    if stat.S_ISREG(st.st_mode) and st.st_size == 0 and st.st_nlink > 1000:
        return os.path.join(lookup_dir, "dir_%d" % st.st_nlink)
    else:
        return path


def process_directory(lookup_dir, dest, path):
    if os.path.islink(dest):
        os.unlink(dest)
    if not os.path.isdir(dest):
        os.mkdir(dest)
    path = resolve_path(lookup_dir, path)

    for filename in os.listdir(path):
        full_filename = os.path.join(path, filename)
        full_filename = resolve_path(lookup_dir, full_filename)
        dest_filename = os.path.join(dest, filename)

        if os.path.isdir(full_filename):
            process_directory(lookup_dir, dest_filename, full_filename)
        else:
            if os.path.islink(dest_filename):
                os.unlink(dest_filename)
            if not os.path.isdir(dest_filename):
                os.symlink(full_filename, dest_filename)

def main(dest, path):
    lookup_dir = find_lookup_dir(path)
    process_directory(lookup_dir, dest, path)

def print_usage_exit():
    print >>sys.stderr, "Usage: %s dest path" % sys.argv[0]
    sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print_usage_exit()

    dest = sys.argv[1]
    path = sys.argv[2]

    main(dest, path)

