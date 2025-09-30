# Data Center Site Analyzer - Streamlit Deployment Guide

## Overview
Your ADK-based data center analysis tool has been successfully migrated to Streamlit with minimal changes to core functionality.

## Files Modified/Created

### Modified Files:
- **agent/agent.py**: Updated environment variables and replaced ADK Runner with Streamlit UI
- **agent/requirements.txt**: Added Streamlit, removed python-dotenv

### New Files:
- **app.py**: Root entry point for Streamlit
- **.streamlit/secrets.toml**: Template for API key configuration

## Local Development Setup

1. **Install dependencies:**
   ```bash
   pip install -r agent/requirements.txt
   ```

2. **Configure secrets:**
   - Edit `.streamlit/secrets.toml` with your actual API keys:
     ```toml
     GOOGLE_MAPS_API_KEY = "your_actual_google_maps_key"
     GEMINI_API_KEY = "your_actual_gemini_key"
     GEMINI_MODEL = "gemini-2.5-flash"
     ```

3. **Run the application:**
   ```bash
   streamlit run app.py
   ```

## Streamlit Community Cloud Deployment

1. **Upload your code** to a GitHub repository (exclude .streamlit/secrets.toml)

2. **Deploy on Streamlit Cloud:**
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Connect your GitHub repository
   - Set main file path to: `app.py`

3. **Configure secrets** in the Streamlit Cloud interface:
   - Go to your app settings
   - Add secrets:
     ```toml
     GOOGLE_MAPS_API_KEY = "your_actual_google_maps_key"
     GEMINI_API_KEY = "your_actual_gemini_key"
     GEMINI_MODEL = "gemini-2.5-flash"
     ```

## What's Preserved
- ✅ All agent functionality (power, network, climate, risk, ESG, regulatory, hyperscaler)
- ✅ Database operations and report storage
- ✅ Google Maps integration for location intelligence
- ✅ Comprehensive datacenter analysis capabilities
- ✅ PDF report generation
- ✅ Synthesis agents and parallel processing

## New Features
- 🎉 Modern chat interface with Streamlit
- 🎉 Real-time conversation history
- 🎉 Secure secrets management
- 🎉 Easy cloud deployment
- 🎉 Responsive web interface

## Important Notes
- The wrapper classes in `synthesis_agents.py` retain their internal `os.getenv('GEMINI_API_KEY')` calls as designed - Streamlit automatically loads secrets into environment variables
- All core business logic remains unchanged
- No changes needed to domain-specific agents or database functionality

## Troubleshooting
- If you see import errors, ensure all dependencies are installed from requirements.txt
- If API keys aren't working, double-check your secrets configuration
- For deployment issues, verify the main file path is set to `app.py` in Streamlit Cloud settings