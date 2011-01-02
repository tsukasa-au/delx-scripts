#!/bin/bash

PIDFILE="$HOME/.mediawrap.pid"
PULSESTATE="$HOME/.pulseaudio.state"
KEYPATH="/apps/gnome_settings_daemon/keybindings"

while true; do
	if [ ! -r "$PIDFILE" ]; then
		break
	fi
	if [ "$(ps -o cmd= -p "$(cat "$PIDFILE")" | wc -l)" -eq 0 ]; then
		break
	fi
	sleep 0.5
done

# Disable volume keys
gconftool --set --type string "$KEYPATH/volume_up" ''
gconftool --set --type string "$KEYPATH/volume_down" ''
gconftool --set --type string "$KEYPATH/volume_mute" ''

# Unmute everything and turn volume to full
pacmd 'dump' | grep 'set-sink' > "$PULSESTATE"
cat "$PULSESTATE" | grep 'set-sink-mute' | awk '{print $2;}' | \
	while read device; do
		pacmd "set-sink-volume $device 0x10000" > /dev/null
		pacmd "set-sink-mute $device no" > /dev/null
	done

# Run the program
"$@"

# Restore volume levels and mute status
cat "$PULSESTATE" | pacmd > /dev/null

# Enable volume keys
gconftool --set --type string "$KEYPATH/volume_up" 'XF86AudioRaiseVolume'
gconftool --set --type string "$KEYPATH/volume_down" 'XF86AudioLowerVolume'
gconftool --set --type string "$KEYPATH/volume_mute" 'XF86AudioMute'

rm -f "$PIDFILE"

