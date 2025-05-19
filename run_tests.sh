#!/usr/bin/env bash

DB_IP=PC1-0136-A FAIR3R_CUSTOM_OVERLAY_CONTEXT=test pytest --cov=fair3r_custom_overlay fair3r_custom_overlay/tests

# pour lancer un seul test
# FAIR3R_CUSTOM_OVERLAY_CONTEXT=test pytest FAIR3R_CUSTOM_OVERLAY/tests/test_import_request.py::TestFull Import::test_request
