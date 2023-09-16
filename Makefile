# with timeout ~6hrs
SHELL = /bin/bash

all: run

run: bot.py
	timeout 21500 python bot.py; \
	status=$${?}; \
	if (( $${status} == 124 )); \
	then exit 0; \
	else exit $${status}; \
	fi;

.PHONY: bot.py
bot.py:
	[ -f bot.py ] && echo "Running bot..." || \
	echo "Bot is not ready"

ifndef VERBOSE
.SILENT:
endif
