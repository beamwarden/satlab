.PHONY: test install-test

VENV := .venv
PY   := $(VENV)/bin/python

install-test:
	python3 -m venv $(VENV)
	$(PY) -m pip install -q -r agent/requirements-test.txt

test: install-test
	$(VENV)/bin/pytest -q
