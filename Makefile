.PHONY: test install-test

VENV := .venv
PY   := $(VENV)/bin/python

# agent/ and sense-agent/ each define a module named crosslink.py and
# beamwarden.py (deliberately separate copies per deploy target -- see
# CLAUDE.md -- not shared imports). Their test suites must never share a
# sys.path, or one directory's module silently shadows the other's; each
# suite runs as its own isolated pytest invocation, in its own venv, with
# its own pytest.ini (agent/'s is the root pytest.ini; sense-agent/'s is
# sense-agent/pytest.ini) rather than one combined run.
install-test:
	python3 -m venv $(VENV)
	$(PY) -m pip install -q -r agent/requirements-test.txt -r sense-agent/requirements-test.txt

test: install-test
	$(VENV)/bin/pytest -q
	cd sense-agent && ../$(VENV)/bin/pytest -q
