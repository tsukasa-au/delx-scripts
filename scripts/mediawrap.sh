#!/bin/bash

LOCKFILE="$HOME/.mediawrap.lock"
PULSESTATE="$HOME/.pulseaudio.state"

(
if ! flock -w 10 -x 200; then
	echo "Failed to get a lock!"
	exit 1
fi
echo "got lock"

# Unmute everything and turn volume to full
if [ "$1" = "--max-volume" ]; then
	echo "max volume"
	max_volume=1
	shift
	pacmd 'dump' | grep 'set-sink' > "$PULSESTATE"
	cat "$PULSESTATE" | grep 'set-sink-mute' | awk '{print $2;}' | \
		while read device; do
			pacmd "set-sink-volume $device 0x10000" > /dev/null
			pacmd "set-sink-mute $device no" > /dev/null
		done
fi

# Switch volume keys to F9/F10 with xmodmap
if [ "$1" = "--switch-volume-keys" ]; then
	echo "switch volume"
	switch_volume=1
	shift
	xmodmap -e 'keycode 122 = F9'
	xmodmap -e 'keycode 123 = F10'
fi


# Run the program
"$@" &> /dev/null


# Restore volume levels and mute status
if [ -n "$max_volume" ]; then
	cat "$PULSESTATE" | pacmd > /dev/null
fi

# Restore volume keys
if [ -n "$switch_volume" ]; then
	xmodmap -e 'keycode 122 = XF86AudioLowerVolume'
	xmodmap -e 'keycode 123 = XF86AudioRaiseVolume'
fi

) 200>"$LOCKFILE"

# Cleanup so other programs can start
rm -f "$LOCKFILE"

