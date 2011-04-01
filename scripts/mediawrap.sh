#!/bin/bash

PIDFILE="$HOME/.mediawrap.pid"
PULSESTATE="$HOME/.pulseaudio.state"
KEYPATH="/apps/gnome_settings_daemon/keybindings"

# Wait for any other wrapped software to finish
for i in $(seq 6); do
	if [ ! -r "$PIDFILE" ]; then
		break
	fi
	if [ "$(ps -o cmd= -p "$(cat "$PIDFILE")" | wc -l)" -eq 0 ]; then
		break
	fi
	sleep 0.5
done
if [ -r "$PIDFILE" ]; then
	exit 1
fi
echo $$ > "$PIDFILE"

# Disable volume keys
if [ "$1" = "--disable-volume-keys" ]; then
	disable_volume_keys=1
	shift
	gconftool --set --type string "$KEYPATH/volume_up" ''
	gconftool --set --type string "$KEYPATH/volume_down" ''
	gconftool --set --type string "$KEYPATH/volume_mute" ''
fi

# Unmute everything and turn volume to full
if [ "$1" = "--max-volume" ]; then
	max_volume=1
	shift
	pacmd 'dump' | grep 'set-sink' > "$PULSESTATE"
	cat "$PULSESTATE" | grep 'set-sink-mute' | awk '{print $2;}' | \
		while read device; do
			pacmd "set-sink-volume $device 0x10000" > /dev/null
			pacmd "set-sink-mute $device no" > /dev/null
		done
fi

# Run the program
"$@" &> /dev/null


# Restore volume levels and mute status
if [ -n "$max_volume" ]; then
	cat "$PULSESTATE" | pacmd > /dev/null
fi

# Enable volume keys
if [ -n "$disable_volume_keys" ]; then
	gconftool --set --type string "$KEYPATH/volume_up" 'XF86AudioRaiseVolume'
	gconftool --set --type string "$KEYPATH/volume_down" 'XF86AudioLowerVolume'
	gconftool --set --type string "$KEYPATH/volume_mute" 'XF86AudioMute'
fi

# Cleanup so other programs can start
rm -f "$PIDFILE"

