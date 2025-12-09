"""Authentication utilities for Chirisa AI."""

import streamlit as st
from config.settings import AUTH_USERNAME, AUTH_PASSWORD


def check_authentication() -> bool:
    """Check if user is authenticated.

    Returns:
        bool: True if authenticated, False otherwise
    """
    return st.session_state.get("authenticated", False)


def get_current_user() -> str:
    """Get the current authenticated username.

    Returns:
        str: Username of authenticated user, or empty string if not authenticated
    """
    return st.session_state.get("username", "")


def show_login_form():
    """Display login form and handle authentication."""
    st.markdown(
        """
        <div style="text-align: center; padding: 2rem 0;">
            <h1>🏢 Chirisa AI</h1>
            <p style="font-size: 1.2rem; color: #666;">Data Centre Intelligence Platform</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("### 🔐 Login")

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            submit = st.form_submit_button("Login", width='stretch')

            if submit:
                from config.settings import USERS
                if username in USERS and USERS[username] == password:
                    st.session_state.authenticated = True
                    st.session_state.username = username
                    st.rerun()
                else:
                    st.error("Invalid username or password")


def logout():
    """Clear authentication state and logout user."""
    st.session_state.authenticated = False
    if "username" in st.session_state:
        del st.session_state.username
    if "sessions_loaded" in st.session_state:
        del st.session_state.sessions_loaded
    if "sessions" in st.session_state:
        del st.session_state.sessions
    st.rerun()
