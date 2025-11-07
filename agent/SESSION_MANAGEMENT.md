# Session Management for Data Center Analyzer

## Overview

Your Data Center Analyzer now has **persistent session management** that allows users to:
- Continue conversations after server restarts
- Browse session history
- Resume any previous conversation
- All sessions stored in PostgreSQL (Neon)

## Quick Start

### Start the Server
```bash
cd agent
./start_with_sessions.sh
```

Or manually:
```bash
source venv/bin/activate
uvicorn web_server:app --host 0.0.0.0 --port 8000 --reload
```

## Features

### 1. **Main Chat Interface**
- URL: `http://localhost:8000/chat`
- Same ADK web UI you're used to
- Each conversation gets a unique session ID
- Sessions automatically saved to PostgreSQL

### 2. **Session History Browser**
- URL: `http://localhost:8000/sessions`
- Beautiful HTML interface showing all past sessions
- See when each session was created and last updated
- "Resume Chat" button for each session

### 3. **Session API Endpoints**

#### List All Sessions
```bash
curl http://localhost:8000/api/sessions/list
```

Response:
```json
{
  "status": "success",
  "count": 5,
  "sessions": [
    {
      "session_id": "abc-123-def",
      "user_id": "default",
      "app_name": "data-center-analyzer",
      "created_at": "2025-09-30T20:00:00",
      "updated_at": "2025-09-30T20:15:00",
      "resume_url": "/chat?session_id=abc-123-def"
    }
  ]
}
```

#### Get Session Details
```bash
curl http://localhost:8000/api/sessions/{session_id}
```

## How It Works

### Architecture
```
┌─────────────────┐
│   Browser UI    │
│  /chat          │
│  /sessions      │
└────────┬────────┘
         │
┌────────▼────────┐
│  web_server.py  │
│  (FastAPI)      │
│  - ADK routes   │
│  - Custom routes│
└────────┬────────┘
         │
┌────────▼────────┐
│  PostgreSQL     │
│  (Neon)         │
│  - sessions     │
│  - events       │
│  - reports      │
└─────────────────┘
```

### Database Tables

**ADK Session Tables** (managed automatically):
- `sessions` - Session metadata (id, user, timestamps, state)
- `events` - All conversation events (messages, tool calls)
- `user_states` - User-specific state
- `app_states` - Application state

**Your Custom Tables** (for datacenter reports):
- `custom_sessions` - Your conversation history (if using session_manager.py)
- `custom_messages` - Message history
- `reports` - Datacenter analysis reports
- `top_scores_cache` - Performance cache

## Testing Session Persistence

1. **Start the server**
   ```bash
   ./start_with_sessions.sh
   ```

2. **Have a conversation**
   - Go to http://localhost:8000/chat
   - Ask: "Analyze Dubai as a datacenter location"
   - Note your session ID in the URL

3. **Check sessions are saved**
   ```bash
   curl http://localhost:8000/api/sessions/list
   ```

4. **Stop the server** (Ctrl+C)

5. **Restart the server**
   ```bash
   ./start_with_sessions.sh
   ```

6. **View session history**
   - Go to http://localhost:8000/sessions
   - See your previous conversation listed
   - Click "Resume Chat" - it should continue where you left off!

## Differences from `adk web`

| Feature | `adk web` | `web_server.py` |
|---------|-----------|-----------------|
| Basic chat UI | ✅ | ✅ |
| Session persistence | ✅ | ✅ |
| Session history UI | ❌ | ✅ |
| API to list sessions | ❌ | ✅ |
| Resume past chats | Manual URL only | UI + API |
| Custom endpoints | ❌ | ✅ Easy to add |

## Extending the System

### Add More Endpoints

Edit `web_server.py` and add:

```python
@app.get("/api/custom-endpoint")
async def my_custom_endpoint():
    # Your code here
    return {"status": "success"}
```

### Customize Session Browser

The HTML is embedded in `web_server.py` at the `/sessions` endpoint. You can:
- Style it differently
- Add search/filtering
- Show conversation previews
- Add delete buttons

### Integrate with Streamlit

For your eventual Streamlit deployment:

```python
import streamlit as st
import requests

# List sessions
sessions = requests.get("http://localhost:8000/api/sessions/list").json()

# Show in Streamlit
for session in sessions['sessions']:
    if st.button(f"Resume {session['session_id']}"):
        # Load that session in your Streamlit UI
        pass
```

## Environment Variables

Make sure your `.env` has:
```bash
DATABASE_URL=postgresql://user:pass@host/dbname
GOOGLE_MAPS_API_KEY=your_key
GEMINI_API_KEY=your_key
```

## Troubleshooting

### Sessions not appearing?
- Check PostgreSQL connection: `psql $DATABASE_URL -c "SELECT COUNT(*) FROM sessions"`
- Verify you had a conversation (sessions only created after first message)

### Can't resume session?
- Session ID must be exact (copy from URL or API)
- User ID must match (default is "default")

### Database errors?
- Run: `python3 -c "from database import init_database; init_database()"`
- Check network connectivity to Neon

## Next Steps

- ✅ PostgreSQL session persistence working
- ✅ Session history browser UI
- ✅ API endpoints for session management
- 🚀 Ready for Streamlit integration
- 🚀 Can add authentication/user management
- 🚀 Can add session search/filtering
- 🚀 Can show conversation previews
