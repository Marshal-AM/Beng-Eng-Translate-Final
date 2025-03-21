#!/bin/bash

# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License

# Display banner
echo "=================================="
echo "Voice Translation App Launcher"
echo "=================================="
echo "Starting HTTP server on port 8000"
echo "Visit http://localhost:8000 in your browser"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=================================="

# Set the directory to the script location
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Check if Python 3 is available
if command -v python3 &>/dev/null; then
    PYTHON=python3
elif command -v python &>/dev/null; then
    PYTHON=python
else
    echo "Error: Python 3 is required but not found"
    exit 1
fi

# Run the server script
$PYTHON server.py 