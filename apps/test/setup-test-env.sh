#!/bin/bash

# Setup script for AI RAG Test Environment
# This script creates a virtual environment and installs test dependencies

set -e

# Colors for output
BLUE='\033[0;34m'
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

print_info "Setting up test environment in $SCRIPT_DIR..."

# Check for python3
if ! command -v python3 &> /dev/null; then
    print_error "python3 is not installed. Please install it to continue."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    print_info "Creating virtual environment..."
    python3 -m venv .venv
    print_success "Virtual environment created."
else
    print_info "Virtual environment (.venv) already exists."
fi

# Activate virtual environment and install dependencies
print_info "Installing dependencies from requirements.txt..."
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

print_success "Test environment setup complete!"
print_info "To run tests, activate the environment with: source apps/test/.venv/bin/activate"
