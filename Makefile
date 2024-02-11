PREFIX = /usr/local

install:
	mkdir -p $(DESTDIR)$(PREFIX)/bin
	cp -f habits.py $(DESTDIR)$(PREFIX)/bin/habits

uninstall:
	rm -f $(DESTDIR)$(PREFIX)/bin/habits

.PHONY: install uninstall
