"""
Shared Gemini model configuration for all agents
Centralized configuration for model selection, retry behavior, and planning

Requires:
- google-adk >= 1.15.0
- google-genai >= 0.3.0
- google-generativeai >= 0.8.0
"""
import os
from google.adk.models import Gemini
from google.adk.planners import BuiltInPlanner
from google.genai import types

# Allow environment variable override for model name (backwards compatibility)
MODEL_NAME = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash-preview-09-2025')

# Retry configuration for API resilience
RETRY_OPTIONS = types.HttpRetryOptions(
    initial_delay=1,      # Start with 1 second delay
    max_delay=10,         # Cap at 10 seconds between retries
    attempts=3            # Total of 3 attempts before failing
)

# Thinking configuration for Gemini 2.5 built-in planner
THINKING_CONFIG = types.ThinkingConfig(
    include_thoughts=False,    # Don't include raw thinking in response
    thinking_budget=10048      # Limit thinking tokens for cost control
)

# Create configured Gemini model instance
gemini_model = Gemini(
    model=MODEL_NAME,
    retry_options=RETRY_OPTIONS
)

# Create built-in planner with thinking configuration
built_in_planner = BuiltInPlanner(
    thinking_config=THINKING_CONFIG
)
