# app.py - Streamlit Entry Point for Data Center Site Analyzer
# This file acts as the main entry point for Streamlit deployment

import sys
import os

# Add the current directory to the Python path to resolve imports
sys.path.insert(0, ".")

# Import and run the main Streamlit application
from agent.agent import run_datacenter_app_ui

if __name__ == "__main__":
    run_datacenter_app_ui()