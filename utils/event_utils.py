"""Utilities for reconstructing messages from ADK events."""

from __future__ import annotations

import logging
from typing import Any

MessageDict = dict[str, Any]
logger = logging.getLogger(__name__)


def reconstruct_messages_from_events(events: list[Any]) -> list[MessageDict]:
    """
    Reconstruct chat messages from ADK events.

    Args:
        events: List of ADK Event objects

    Returns:
        List of message dictionaries with role, content, and optional type/tool info
    """
    messages: list[MessageDict] = []

    for event in events:
        # Skip events without content
        if not event.content or not event.content.parts:
            continue

        # Check for tool calls
        try:
            function_calls = event.get_function_calls()
            if function_calls:
                messages.extend([
                    {
                        "role": "assistant",
                        "type": "tool_call",
                        "tool_name": func_call.name,
                        "args": func_call.args,
                    }
                    for func_call in function_calls
                ])
        except (AttributeError, TypeError) as e:
            logger.debug("Error getting function calls: %s", e)

        # Check for tool responses
        try:
            function_responses = event.get_function_responses()
            if function_responses:
                messages.extend([
                    {
                        "role": "assistant",
                        "type": "tool_response",
                        "tool_name": func_response.name,
                        "response": func_response.response,
                    }
                    for func_response in function_responses
                ])
        except (AttributeError, TypeError) as e:
            logger.debug("Error getting function responses: %s", e)

        # Check for text content - safely access parts[0]
        try:
            if len(event.content.parts) > 0 and event.content.parts[0].text:
                text = event.content.parts[0].text
                role = "user" if event.author == "user" else "assistant"
                messages.append({"role": role, "content": text})
        except (AttributeError, IndexError, TypeError) as e:
            logger.debug("Error getting text content: %s", e)

    return messages
