"""Simple agent with time tool functionality."""

from datetime import UTC, datetime

from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool


def get_current_time() -> str:
    """Returns the current time in a readable format."""
    now = datetime.now(UTC)
    return now.strftime("%Y-%m-%d %H:%M:%S")


def create_time_agent() -> LlmAgent:
    """Creates a simple agent with a time tool."""
    time_tool = FunctionTool(func=get_current_time)

    return LlmAgent(
        name="time_assistant",
        model="gemini-2.5-flash-preview-09-2025",
        instruction=(
            "You are a helpful assistant that can tell the current time. "
            "Use the get_current_time tool when users ask about the time."
        ),
        description=(
            "An assistant that can answer questions and provide the current time."
        ),
        tools=[time_tool],
    )
