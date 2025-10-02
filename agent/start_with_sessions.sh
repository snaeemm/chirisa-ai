#!/bin/bash
# Start Data Center Analyzer with Session Management

echo "🚀 Starting Data Center Analyzer with Session Management"
echo ""
echo "📊 Initialize PostgreSQL database..."
source venv/bin/activate
python3 -c "from database import init_database; init_database()"

echo ""
echo "🌐 Starting web server..."
echo "   Main Chat UI: http://localhost:8000/chat"
echo "   Session History: http://localhost:8000/sessions"
echo "   API Docs: http://localhost:8000/docs"
echo ""

uvicorn web_server:app --host 0.0.0.0 --port 8000 --reload
