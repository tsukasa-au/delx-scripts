CFLAGS     := -Wall -W $(CFLAGS)
FRAMEWORKS := -std=c99 -framework Foundation -framework AddressBook

ab2mutt: ab2mutt.m
	$(CC) $< -o $@ $(CFLAGS) $(FRAMEWORKS)

clean:
	rm -f ab2mutt

.PHONY: clean
