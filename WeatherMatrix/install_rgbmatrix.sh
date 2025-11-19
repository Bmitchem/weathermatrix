#!/bin/bash
# Install script for rpi-rgb-led-matrix library
# This script clones, builds, and installs the RGB matrix library for Raspberry Pi

set -e  # Exit on error

echo "Installing rpi-rgb-led-matrix library..."

# Check if we're on a Raspberry Pi (optional check)
if [ ! -f /proc/device-tree/model ] || ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "Warning: This doesn't appear to be a Raspberry Pi."
    echo "The rgbmatrix library may not work correctly on this system."
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPO =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Check if git is installed
if ! command -v git &> /dev/null; then
    echo "Error: git is not installed. Installing..."
    sudo apt-get update
    sudo apt-get install -y git
fi

# Check if build tools are installed
if ! command -v make &> /dev/null || ! command -v g++ &> /dev/null; then
    echo "Installing build dependencies..."
    sudo apt-get update
    sudo apt-get install -y build-essential python3-dev cython3
fi

# Determine installation directory
INSTALL_DIR="${HOME}/rpi-rgb-led-matrix"
REPO_URL="https://github.com/hzeller/rpi-rgb-led-matrix.git"

# Check if directory already exists
if [ -d "$INSTALL_DIR" ]; then
    echo "Directory $INSTALL_DIR already exists."
    read -p "Remove and re-clone? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Removing existing directory..."
        rm -rf "$INSTALL_DIR"
    else
        echo "Using existing directory. Skipping clone."
        SKIP_CLONE=true
    fi
fi

# Clone the repository if needed
if [ "$SKIP_CLONE" != "true" ]; then
    echo "Cloning rpi-rgb-led-matrix repository..."
    git clone "$REPO_URL" "$INSTALL_DIR"
fi

# Build Python bindings
echo "Building Python bindings..."
cd "$INSTALL_DIR"
make build-python

# Install Python bindings
echo "Installing Python bindings (requires sudo)..."
sudo make install-python

echo ""
echo "✓ rpi-rgb-led-matrix library installed successfully!"
echo ""
echo "The library is now available. You can test it with:"
echo "  cd $INSTALL_DIR/examples-api-use"
echo "  sudo ./demo -D 0"
echo ""
echo "Or use it in your Python scripts:"
echo "  from rgbmatrix import RGBMatrix, RGBMatrixOptions"

