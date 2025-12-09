# File Upload Feature Documentation

## Overview

The file upload feature enables users to upload documents (PDFs, Word files, images, etc.) directly in the Streamlit chat interface. Uploaded files are automatically processed to extract text content, which is then included as context for AI conversations.

## Features

✅ **Multi-file Upload Support**
- Upload multiple files at once
- Support for various file types (PDF, DOCX, XLSX, PPTX, TXT, PNG, JPG)

✅ **Automatic Text Extraction**
- Uses Google Gemini API for intelligent text extraction
- Direct DOCX parsing using python-docx library
- Preserves document structure (headings, paragraphs, tables)

✅ **Document Classification**
- Automatic classification into: RFP, Meeting Notes, or Other
- Helps organize and identify document types

✅ **Context Integration**
- Extracted text automatically included in chat messages
- AI can reference and analyze uploaded documents
- File content preserved for session duration

✅ **File Management**
- View uploaded files in chat or sidebar
- Remove individual files
- Clear all uploads with one click
- Automatic cleanup of Gemini API files

✅ **Database Storage**
- Optional persistence of file metadata
- Track uploaded files per session
- Support for file history and retrieval

## File Upload UI

### Chat Input Area (Main)
Located below the chat messages, the file upload section includes:

```
📎 Upload documents (PDF, DOCX, images, etc.)
[File picker]                    [Clear All]
```

Files are processed and displayed in an expandable section:
```
📄 Uploaded Files
  📕 document.pdf | Type: RFP | Size: 5000 chars  [✕]
  📗 report.docx | Type: Meeting Notes | Size: 3500 chars  [✕]
```

### Sidebar
Shows a quick summary of uploaded files:
```
📎 Uploaded Files
  2 file(s) uploaded
  📕 document.pdf
  📗 report.docx
  [🗑️ Clear All Files]
```

## Supported File Types

| Extension | Type | Processing |
|-----------|------|-----------|
| `.pdf` | PDF Document | Gemini File API |
| `.docx` | Word Document | Direct parsing + Gemini API |
| `.xlsx` | Excel Spreadsheet | Gemini File API |
| `.pptx` | PowerPoint Presentation | Gemini File API |
| `.txt` | Text File | Direct reading |
| `.png` | Image | Gemini File API |
| `.jpg`, `.jpeg` | Image | Gemini File API |

## Configuration

File upload settings are configured in `config/settings.py`:

```python
# File upload settings
FILE_UPLOAD_MAX_SIZE_MB = 15  # Maximum file size
SUPPORTED_FILE_EXTENSIONS = ['.pdf', '.docx', '.xlsx', '.pptx', '.txt', '.doc', '.xls', '.ppt', '.png', '.jpg', '.jpeg']
FILE_UPLOAD_TEMP_DIR = "/tmp/shaz_uploads"  # Temporary storage
FILE_CLEANUP_INTERVAL_HOURS = 24  # Cleanup interval
```

## Implementation Details

### Document Service (`services/document_service.py`)

Main module for file processing:

**Functions:**

- `extract_document_text(file_path=None, file_object=None)` - Extract text from any supported file
- `extract_text_from_docx(file_path)` - Direct DOCX extraction
- `detect_document_type(text)` - Classify document using Gemini
- `cleanup_gemini_file(file_uri)` - Clean up files from Gemini API

**File Processing Flow:**
1. Validate file type and size
2. Extract text based on file type
3. Detect document type (RFP/Meeting Notes/Other)
4. Return structured result with metadata

### Chat Input Integration (`ui/chat_input.py`)

**Changes:**
- Added `st.file_uploader()` component
- Implemented `process_uploaded_files()` function
- Extended `types.Content` to include file context
- Added file display and management UI

**File Attachment Flow:**
1. User selects files via uploader
2. Files processed and stored in session state
3. User types message
4. Extracted text appended to message as context
5. AI receives enhanced prompt with document content

### Database Storage (`agent/database.py`)

**New Table: `uploaded_files`**
```sql
CREATE TABLE uploaded_files (
    id SERIAL PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id TEXT,
    filename TEXT NOT NULL,
    file_type TEXT,
    document_type TEXT,
    text_content TEXT,
    file_size_bytes INTEGER,
    gemini_file_uri TEXT,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES custom_sessions(session_id)
)
```

**Indexes for Performance:**
- `idx_uploaded_files_session` - Fast retrieval by session
- `idx_uploaded_files_user` - User-level file management
- `idx_uploaded_files_date` - Sort by upload time

### Sidebar Integration (`ui/sidebar.py`)

Added file management section showing:
- Count of uploaded files
- File list with icons
- Clear all files button
- File metadata (type, size)

## Usage Flow

### Step 1: Upload Files
```
User clicks on file picker → Selects one or more files
System shows "Processing files..." spinner
Files are extracted and added to uploaded files list
```

### Step 2: View Files
```
Files displayed in "Uploaded Files" section
Each file shows:
  - File icon (📕 PDF, 📗 DOCX, 🖼️ Image, etc.)
  - Filename
  - Document type (if detected)
  - Character count
  - Remove button (✕)
```

### Step 3: Use in Chat
```
User types a message
System appends extracted text from files
Message sent to AI with enhanced context
AI can reference and analyze uploaded documents
```

### Step 4: Manage Files
```
Remove individual file: Click ✕ button
Clear all files: Click "Clear All" button
Files removed from session state and Gemini API
```

## Session State Management

Files are stored in `st.session_state.processed_files`:

```python
{
    'status': 'success',
    'filename': 'document.pdf',
    'text': '... extracted text ...',
    'file_uri': 'files/abc123',  # Gemini File API URI
    'document_type': 'RFP'
}
```

Session state provides:
- Per-session file persistence
- Quick access without database roundtrips
- Automatic cleanup on session end

## Error Handling

**File Validation Errors:**
- Unsupported file type → ❌ Error message shown
- File too large → ❌ Error with size info
- Extraction failed → ❌ Error with details

**UI Feedback:**
- Processing: 🔄 Spinner with status
- Success: ✅ Confirmation message
- Error: ❌ Error message in red

## Performance Considerations

**Optimizations:**
- Direct DOCX parsing (faster than Gemini for text-only)
- Batch file processing with progress tracking
- Session state caching (no DB access for active session)
- Async processing (non-blocking UI)

**Limits:**
- Max file size: 15 MB (configurable)
- Max files per upload: Unlimited
- Token limit: Gemini's context window (integrated into chat)

## Dependencies

New packages required:
```
python-docx>=1.1.0      # DOCX file parsing
pypdf2>=3.0.0          # PDF extraction (optional, using Gemini API)
pillow>=10.0.0         # Image processing (optional, using Gemini API)
```

Already installed:
- `google-generativeai` - Gemini API
- `streamlit` - UI framework
- `psycopg2-binary` - Database (optional)

## Security Considerations

✅ **File Type Validation**
- Whitelist of supported extensions
- MIME type checking (future enhancement)

✅ **File Size Limits**
- Maximum 15 MB per file
- Configurable in settings

✅ **Temporary File Cleanup**
- Automatically delete temp files after extraction
- Scheduled cleanup of old uploads (future)

⚠️ **Future Enhancements**
- Virus scanning integration
- Rate limiting for uploads
- User quota management
- Encrypted storage for sensitive files

## Troubleshooting

### Files Not Being Processed
- Check file format is in supported list
- Verify file size < 15 MB
- Check Google API key is valid
- Look for error messages in UI

### Text Not Extracted
- Some PDFs may not have extractable text
- Scanned images require OCR (Gemini handles this)
- Check file is not corrupted

### Gemini API Errors
- Verify `GOOGLE_API_KEY` environment variable
- Check API quota and rate limits
- Ensure correct model name in settings

### Missing Dependencies
```bash
pip install -r requirements.txt
```

## Future Enhancements

- [ ] OCR for scanned documents
- [ ] Text preview in UI
- [ ] Download extracted text
- [ ] Drag-and-drop file upload
- [ ] Batch processing with progress bar
- [ ] File compression for storage
- [ ] Share uploaded files between sessions
- [ ] Document versioning
- [ ] Full-text search across files
- [ ] Integration with Google Drive

## Technical Architecture

```
User Input (File Upload)
    ↓
Streamlit File Uploader
    ↓
process_uploaded_files()
    ↓
extract_document_text()
    ├─→ TXT: Direct read
    ├─→ DOCX: python-docx
    └─→ Others: Gemini File API
    ↓
Document Type Detection
    ├─→ Gemini Classification
    └─→ Auto-Detection
    ↓
Session State Storage
    ├─→ Chat Display
    ├─→ Sidebar Display
    └─→ Message Context
    ↓
Chat Context Integration
    ├─→ User Message
    ├─→ + File Content
    └─→ → AI Agent
    ↓
Response Generation
```

## API Integration

### Google Gemini File API

Used for advanced document processing:
```python
# Upload file
uploaded_file = client.files.upload(file=file_path)

# Extract with model
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[extraction_prompt, uploaded_file]
)

# Cleanup
client.files.delete(name=uploaded_file.name)
```

### Database Integration (Optional)

Files can be persisted:
```python
# Store metadata
INSERT INTO uploaded_files (
    session_id, filename, document_type, text_content
) VALUES (...)

# Retrieve files
SELECT * FROM uploaded_files
WHERE session_id = %s
ORDER BY uploaded_at DESC
```

## Examples

### Basic File Upload and Query
```
User uploads: "report.pdf" (RFP Document)
Message: "What are the main requirements?"
AI: [Analyzes PDF] "Based on the RFP you uploaded, the main requirements are..."
```

### Multi-File Analysis
```
User uploads:
  - requirements.docx
  - budget.xlsx
  - timeline.pdf

Message: "Can you compare the requirements with our budget?"
AI: [Cross-references all files] "Yes, the requirements align with..."
```

### Document Classification
```
User uploads: meeting_notes.docx
System detects: "Meeting Notes"
AI: Processes as discussion notes with context-aware responses
```

## Support and Issues

For issues or questions:
1. Check file format and size
2. Verify API keys are configured
3. Check error messages in UI
4. Review logs for detailed errors
5. Ensure all dependencies installed

## License

Part of the Chirisa AI application
