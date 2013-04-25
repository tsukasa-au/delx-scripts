#!/bin/bash

killall xbmc.bin
sleep 1
killall -9 xbmc.bin


echo "$@"
"$@"


sleep 1
exec $(grep Exec ~/Desktop/xbmc.desktop | cut -d= -f2)

