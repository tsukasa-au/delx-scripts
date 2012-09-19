CFLAGS     := -Wall -W -std=c99 $(CFLAGS)
LDFLAGS    := $(LDFLAGS)
FRAMEWORKS := -framework Foundation -framework AddressBook
TARGETS    := ab2mutt

all: $(TARGETS)

%: %.m
	$(CC) -o $@ $(CFLAGS) $(LDFLAGS) $(FRAMEWORKS) $<

clean:
	rm -f $(TARGETS)

.PHONY: clean
