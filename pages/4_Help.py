"""Help page with user guide and documentation."""

import streamlit as st
from dotenv import load_dotenv

from config.settings import PAGE_CONFIG
from services.agent_service import init_agent
from services.session_service import initialize_sessions
from utils.auth import check_authentication, show_login_form

load_dotenv()

st.set_page_config(**PAGE_CONFIG)

if not check_authentication():
    show_login_form()
    st.stop()

runner, session_service = init_agent()
initialize_sessions(session_service)

with st.sidebar:
    from ui.sidebar import render_minimal_sidebar
    render_minimal_sidebar()

st.title("📖 Help & User Guide")
st.markdown("---")

st.markdown("""
## Welcome to Chirisa AI

Chirisa AI is a data centre intelligence platform that provides comprehensive site analysis across multiple domains.

### 🚀 Quick Start

1. **Start a Conversation**: Click **➕ New Chat** in the sidebar to begin
2. **Ask About Locations**: Request analysis for specific data centre locations
3. **View Reports**: Access generated reports from the **Reports** page
4. **Switch Sessions**: Navigate between different conversations using the sidebar

### 💬 Using the Assistant

The AI Assistant can help you with:

- **Location Analysis**: Ask about data centre viability for specific cities/regions
- **Domain Insights**: Request information on power, network, climate, regulations, etc.
- **Comparative Analysis**: Compare multiple locations
- **Strategic Recommendations**: Get deployment and planning advice

**Example Questions:**
- "Analyze the viability of Sydney, Australia for a data centre"
- "Compare power infrastructure in Singapore vs Tokyo"
- "What are the regulatory requirements for data centres in Germany?"

### 📊 Reports Page

- **Browse Reports**: View all generated analyses
- **Search**: Filter reports by location or country
- **Details**: Click any report to see full analysis with scores and recommendations
- **Delete**: Remove reports you no longer need

### 🔍 Understanding Report Scores

Reports include composite scores across 7 domains:

- 🟢 **4.0+**: Excellent - Highly suitable
- 🟡 **3.0-3.9**: Good - Generally suitable with minor considerations
- 🟠 **2.0-2.9**: Fair - Some significant challenges
- 🔴 **Below 2.0**: Poor - Major obstacles present

### 👥 User Accounts

- Each user has their own **private chat sessions**
- **Reports are shared** across all users
- Use the **🚪 Logout** button to switch accounts

### 💡 Tips

- Sessions are automatically saved as you chat
- Reports persist in the database for future reference
- Use descriptive queries for better analysis results
- The AI considers multiple factors: power, network, climate, regulations, ESG, risks, and hyperscaler presence

### ⚙️ Technical Details

**Analysis Domains:**
1. **Power & Energy**: Grid capacity, renewable options, costs
2. **Network Infrastructure**: Connectivity, latency, bandwidth
3. **Climate & Environment**: Temperature, natural disaster risks
4. **Regulatory Environment**: Data laws, tax policies, incentives
5. **ESG Factors**: Sustainability, carbon footprint
6. **Risk Assessment**: Political, economic, operational risks
7. **Hyperscaler Presence**: Existing major cloud infrastructure

### 🆘 Need Help?

If you encounter issues or have questions about specific features, please contact your system administrator.

---

**Version**: MVP v1
**Powered by**: Google Gemini AI & PostgreSQL
""")

st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("💬 Go to Assistant", width='stretch', type="primary"):
        st.switch_page("Assistant.py")

with col2:
    if st.button("📊 View Reports", width='stretch', type="secondary"):
        st.switch_page("pages/3_Reports.py")

with col3:
    if st.button("🚪 Logout", width='stretch'):
        from utils.auth import logout
        logout()
