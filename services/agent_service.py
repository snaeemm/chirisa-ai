"""Service for initializing and managing ADK agents."""

from __future__ import annotations

import streamlit as st
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService

from config.settings import APP_NAME, DATABASE_URL
from agent.agent import root_agent


@st.cache_resource
def init_agent() -> tuple[Runner, DatabaseSessionService]:
    """
    Initialize the ADK agent, runner, and session service.

    Returns:
        Tuple of (Runner, DatabaseSessionService)
    """
    # Use the real datacenter analysis agent
    agent = root_agent

    # Initialize database session service with connection pool settings
    # pool_pre_ping=True: Test connections before use (handles stale SSL connections)
    # pool_recycle=300: Recycle connections after 5 minutes to prevent stale connections
    session_service = DatabaseSessionService(
        db_url=DATABASE_URL,
        pool_pre_ping=True,
        pool_recycle=300,
        pool_size=5,
        max_overflow=10
    )

    # Create runner
    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service
    )

    return runner, session_service
