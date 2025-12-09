# File Upload Feature - Quick Start Guide

## What Was Added

Your Streamlit chat app now supports uploading documents directly! Users can upload PDFs, Word documents, images, and more, and the AI will analyze them alongside regular chat messages.

## How Users Use It

1. **Open Chat** - Navigate to Assistant page
2. **Upload Files** - Click on the file uploader area below the chat
3. **Select Files** - Choose one or more files (PDF, DOCX, TXT, images, etc.)
4. **Files Appear** - See uploaded files listed below uploader
5. **Type Message** - Ask questions about the files
6. **AI Responds** - AI analyzes files + your question together

## Supported File Types

| Type | Icon | Processing |
|------|------|-----------|
| PDF | 📕 | Gemini API |
| Word (.docx) | 📗 | Direct parsing |
| Excel | 📊 | Gemini API |
| PowerPoint | 📈 | Gemini API |
| Text (.txt) | 📄 | Direct read |
| Images (PNG/JPG) | 🖼️ | Gemini API (OCR) |

## Configuration

File settings in `config/settings.py`:
```python
FILE_UPLOAD_MAX_SIZE_MB = 15           # Max per file
SUPPORTED_FILE_EXTENSIONS = [...]      # Allowed types
```

## How It Works (Technical)

### 1. File Upload
```
User → st.file_uploader → Streamlit UploadedFile object
```

### 2. Text Extraction
```
UploadedFile → extract_document_text() → "Extracted text..."
                ├─ TXT: Direct read
                ├─ DOCX: python-docx library
                └─ Others: Gemini File API (deleted after)
```

### 3. Gemini Cleanup
```
✅ Files deleted IMMEDIATELY after extraction (in finally block)
✅ NO persistent local storage
✅ NO Gemini file accumulation
✅ FULLY Streamlit compatible
```

### 4. Session Storage
```
st.session_state.processed_files = [
    {
        'filename': 'report.pdf',
        'text': '... extracted content ...',
        'document_type': 'RFP'
    },
    ...
]
```

### 5. Message Enhancement
```
User message: "Analyze this"
         ↓
Enhanced with file context:
"[Document: report.pdf]\n{content}\n
 [Document: notes.docx]\n{content}\n
 Analyze this"
```

## Key Features

✅ **Multi-File Upload** - Upload multiple files at once

✅ **Automatic Extraction** - Text extracted with Gemini AI

✅ **Document Classification** - Auto-detect: RFP, Meeting Notes, or Other

✅ **Session Persistence** - Files stay during chat session

✅ **File Management** - Remove files individually or all at once

✅ **Smart Cleanup** - Gemini files deleted immediately after use

✅ **Sidebar Integration** - Quick file summary in sidebar

✅ **Error Handling** - Clear error messages for unsupported files

## Code Overview

### Main Components

**`services/document_service.py`** (NEW)
- Handles all file extraction
- In-memory processing only
- Immediate Gemini cleanup

**`ui/chat_input.py`** (Modified)
- File uploader UI
- File processing logic
- File display & management
- Integration with chat context

**`ui/sidebar.py`** (Modified)
- File summary section
- Quick access to file list

## Implementation Details

### Stateless File Processing
```python
# NO local storage
# NO temp files persisted
# ONLY session state

def extract_document_text(file_object):
    """Process file, return extracted text"""
    # TXT: Direct read (instant)
    # DOCX: python-docx (instant)
    # Others: Gemini File API (2-5 seconds)
    #         → File auto-deleted in finally block

    return {
        'status': 'success',
        'filename': '...',
        'text': '...',
        'document_type': '...'
    }
```

### Session State Management
```python
# Initialize
if "processed_files" not in st.session_state:
    st.session_state.processed_files = []

# Add files
st.session_state.processed_files.extend(processed)

# Use in message
for file_data in st.session_state.processed_files:
    parts.append(types.Part(text=f"[Document: {file_data['filename']}]\n{file_data['text']}"))

# Clear
st.session_state.processed_files = []
```

## Performance

| File Type | Processing Time | Method |
|-----------|-----------------|--------|
| TXT (1MB) | ~instant | Direct read |
| DOCX (2MB) | ~instant | python-docx |
| PDF (5MB) | 2-5 sec | Gemini API |
| Image (2MB) | 3-5 sec | Gemini API (OCR) |

## Troubleshooting

### Files Not Showing Up
1. Check file format (in SUPPORTED_FILE_EXTENSIONS)
2. Verify file size < 15MB
3. Look for error message in UI

### Slow Processing
- Normal for PDF/images (Gemini processing)
- Try with TXT or DOCX (faster)

### Error Messages
- **"File too large"** - Reduce to <15MB
- **"Unsupported file type"** - Use supported formats
- **"No text extracted"** - File might be image-only

### Gemini API Issues
- Verify GOOGLE_API_KEY set
- Check API quota
- Try with different file type

## Example Usage

**User uploads:** `project_requirements.pdf`

**User types:** "What are the key requirements?"

**AI receives:**
```
[Document: project_requirements.pdf]
PROJECT REQUIREMENTS v2.1

1. Performance
   - 99.99% uptime
   - <100ms response time
...

Question: What are the key requirements?
```

**AI responds:**
```
Based on the requirements document you uploaded:

The key requirements are:
1. 99.99% uptime SLA
2. Sub-100ms response times
3. [continues analyzing...]
```

## Admin Settings

In `config/settings.py`:

```python
# Max file size in MB
FILE_UPLOAD_MAX_SIZE_MB = 15

# Supported file types
SUPPORTED_FILE_EXTENSIONS = [
    '.pdf', '.docx', '.xlsx', '.pptx',
    '.txt', '.doc', '.xls', '.ppt',
    '.png', '.jpg', '.jpeg'
]

# Temp directory (not actively used - in-memory)
FILE_UPLOAD_TEMP_DIR = "/tmp/shaz_uploads"

# Optional cleanup interval
FILE_CLEANUP_INTERVAL_HOURS = 24
```

## Dependencies

New packages required:
```bash
python-docx>=1.1.0      # DOCX parsing
pypdf2>=3.0.0          # PDF support
pillow>=10.0.0         # Image support
```

Install:
```bash
pip install -r requirements.txt
```

## Database (Optional)

New table for file metadata (optional persistence):
```sql
CREATE TABLE uploaded_files (
    id SERIAL PRIMARY KEY,
    session_id TEXT,
    filename TEXT,
    document_type TEXT,
    text_content TEXT,
    uploaded_at TIMESTAMP DEFAULT NOW()
)
```

Auto-created by `init_database()`.

## Testing

Quick test:
1. Upload a TXT file (fastest)
2. Upload a DOCX file
3. Upload a PDF file
4. Ask AI about the files
5. Remove files and verify they're gone

## Security

✅ File size limits (15MB max)
✅ File type whitelist
✅ Immediate cleanup (no orphaned files)
✅ Session-scoped (no cross-session leaks)

## Monitoring

Check these in production:

1. **Gemini API Usage**
   - Should be stable (files deleted immediately)
   - Spike indicates cleanup failures

2. **Temp Files**
   - Should be empty
   - Cleanup working correctly

3. **Session Memory**
   - Files cleared when session ends
   - No memory leaks

## FAQs

**Q: Can I upload files larger than 15MB?**
A: Increase `FILE_UPLOAD_MAX_SIZE_MB` in settings, but be aware of Gemini API limits (15MB max).

**Q: Do files persist after the chat ends?**
A: No, files are cleared when the session ends. This is by design for memory efficiency.

**Q: What happens to uploaded files?**
A: Files are extracted to text, stored in session state, and Gemini API files are deleted immediately.

**Q: Can I search within uploaded files?**
A: Currently no, but you can ask the AI to search/summarize.

**Q: How many files can I upload?**
A: Unlimited, but use reasonably (session memory constraints).

## Next Steps

1. ✅ Feature is ready to use
2. Test with your documents
3. Adjust file size limits if needed
4. Monitor Gemini API usage
5. Set up error logging for production

## Support

For issues:
1. Check error message in Streamlit UI
2. Verify file format is supported
3. Try with a simple TXT file first
4. Check logs for API errors
5. Review FILE_UPLOAD_IMPLEMENTATION_SUMMARY.md for detailed docs
