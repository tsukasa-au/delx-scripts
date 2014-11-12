.PHONY: all clean

all: xfce4-genmon-script

clean:
	rm -f xfce4-genmon-script

xfce4-genmon-script: xfce4-genmon-script.c
	$(CC) -Wall -Wextra -std=gnu99 -g -lm $< -o $@
