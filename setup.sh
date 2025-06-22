#!/bin/bash

# This script installs and sets up all necessary dependencies for the Tender Agent
# It's primarily designed to run in cloud environments like Streamlit Cloud

echo "Setting up Tender Agent dependencies..."

# Install Python dependencies
pip install -r requirements.txt

# Install Playwright
pip install playwright

# Install Playwright browsers with dependencies
echo "Installing Playwright browsers..."
playwright install --with-deps chromium

echo "Setup complete!"
