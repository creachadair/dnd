##
## Name:     Makefile
## Purpose:  Make script for DND library.
##
## Copyright (C) 2004-2007 Michael J. Fromberger, All Rights Reserved.
##

SRCS=dnd.py setup.py test_dnd.py
OTHER=Makefile README dndedit dndquery groupedit makelist scrapeclass
TESTS=test_dnd.py

.PHONY: clean distclean dist install test

default:
	@ echo "Make targets:"
	@ echo " clean    - clean up temporary files."
	@ echo " install  - install module in site directory."
	@ echo " dist     - make distribution."
	@ echo " install  - install module."
	@ echo " "

clean:
	rm -f *~ *.pyc

install: distclean
	python setup.py install

distclean: clean
	rm -f dnd.zip
	if [ -d build ] ; then rm -rf build ; fi

test: distclean
	for file in $(TESTS) ; do python $${file} ; done

dist: distclean
	mkdir dndlib
	cp $(SRCS) $(OTHER) dndlib/
	zip -9r dnd.zip dndlib/
	rm -rf dndlib/

# Here there be dragons


