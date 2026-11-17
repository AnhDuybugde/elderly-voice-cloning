#!/usr/bin/env bash
set -e
# Run tests filtering out ROS incompatible pytest hooks if ROS is installed on the host
python3 -c "import sys; sys.path = [p for p in sys.path if 'ros' not in p]; import pytest; sys.exit(pytest.main(['tests'] + sys.argv[1:]))" "$@"
