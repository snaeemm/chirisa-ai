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
MODEL_NAME = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')

# Retry configuration for API resilience
# Note: attempts=1 means try once with no retries (saves quota while maintaining quality)
# Retry attempts are for network failures only - they do NOT affect thinking quality
# Thinking quality is controlled by THINKING_CONFIG.thinking_budget (dynamic mode)
RETRY_OPTIONS = types.HttpRetryOptions(
    initial_delay=1,      # Start with 1 second delay
    max_delay=10,         # Cap at 10 seconds between retries (not used with attempts=1)
    attempts=1            # Single attempt - no retries (was 3, reduced to save paid tier quota)
)

# Thinking configuration for Gemini 2.5 built-in planner
# Dynamic mode (-1) lets the model decide how much to think based on task complexity
# Fixed high budgets (like 10048) can exhaust output tokens causing missing fields
THINKING_CONFIG = types.ThinkingConfig(
    include_thoughts=False,    # Don't include raw thinking in response
    thinking_budget=-1         # Dynamic - model balances thinking vs output tokens
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
