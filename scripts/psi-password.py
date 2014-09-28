#!/usr/bin/python2
# Copyright 2007 James Bunton <jamesbunton@fastmail.fm>
# Licensed for distribution under the GPL version 2, check COPYING for details
# Decodes a password taken from a Psi config.xml file


import sys

def decodePassword(passwd, key):
    if not key:
        return passwd
    
    result = ""
    n1 = n2 = 0
    while n1 < len(passwd):
        x = 0
        if n1 + 4 > len(passwd):
            break
        x += int(passwd[n1+0], 16) * 4096
        x += int(passwd[n1+1], 16) * 256
        x += int(passwd[n1+2], 16) * 16
        x += int(passwd[n1+3], 16) * 1
        result += chr(x ^ ord(key[n2]))
        n1 += 4
        n2 += 1
        if n2 >= len(key):
            n2 = 0
    
    return result

if __name__ == "__main__":
    try:
        passwd = sys.argv[1]
        key = sys.argv[2]
    except:
        print >> sys.stderr, "Usage: %s passwd jid" % sys.argv[0]
        sys.exit(1)
    print decodePassword(passwd, key)

