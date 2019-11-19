#!/usr/bin/env bash

DB_IP={{ cookiecutter.db_dev_hostname }} {{ cookiecutter.app|upper }}_CONTEXT=test pytest --cov={{ cookiecutter.app }} {{ cookiecutter.app }}/tests

# pour lancer un seul test
# {{ cookiecutter.app|upper }}_CONTEXT=test pytest {{ cookiecutter.app|upper }}/tests/test_import_request.py::TestFull Import::test_request
