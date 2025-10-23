"""Document extraction and processing service for file uploads."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Dict

import streamlit as st
from dotenv import load_dotenv
from docx import Document
from google import genai

from config.settings import FILE_UPLOAD_MAX_SIZE_MB, SUPPORTED_FILE_EXTENSIONS

# Load environment variables from .env file
load_dotenv(override=True)

# Get API key with better error handling
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise ValueError(
        "GEMINI_API_KEY not found in environment variables. "
        "Please ensure your .env file contains: GEMINI_API_KEY=your_key"
    )

client = genai.Client(api_key=api_key)


def detect_document_type(text: str) -> str:
    """
    Detect document type from extracted text using Gemini.

    Args:
        text: Extracted document text

    Returns:
        Document type: "RFP", "Meeting Notes", or "Other"
    """
    try:
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        prompt = """You must classify this document into EXACTLY ONE of these three categories:

1. RFP - Request for Proposal, tender, RFQ, business opportunity, procurement document
2. Meeting Notes - Meeting minutes, call notes, discussion summary, stakeholder notes
3. Other - Any other type of document

Respond with ONLY the exact category name from above, nothing else. No explanation.

Document text (first 2000 characters):
{text}"""

        response = client.models.generate_content(
            model=model_name,
            contents=[prompt.format(text=text[:2000])]
        )

        raw_response = response.text.strip() if response and hasattr(response, 'text') else "Other"

        # More flexible parsing - look for keywords in the response
        if "RFP" in raw_response and "Meeting" not in raw_response:
            doc_type = "RFP"
        elif "Meeting" in raw_response:
            doc_type = "Meeting Notes"
        elif "Other" in raw_response:
            doc_type = "Other"
        else:
            # Last resort: check first word
            first_word = raw_response.split()[0] if raw_response.split() else ""
            if first_word in ["RFP", "Meeting", "Other"]:
                doc_type = first_word if first_word != "Meeting" else "Meeting Notes"
            else:
                st.warning(f"Could not parse document type: '{raw_response}', using 'Other'")
                doc_type = "Other"

        return doc_type

    except Exception as e:
        st.warning(f"Failed to detect document type: {e}")
        return "Other"


def extract_text_from_docx(file_path: str) -> str:
    """
    Extract text from a DOCX file using python-docx library.

    Args:
        file_path: Path to the DOCX file

    Returns:
        Extracted text content
    """
    try:
        doc = Document(file_path)
        text_parts = []

        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_parts.append(paragraph.text)

        # Also extract text from tables
        for table in doc.tables:
            for row in table.rows:
                row_text = []
                for cell in row.cells:
                    row_text.append(cell.text)
                if any(row_text):
                    text_parts.append(" | ".join(row_text))

        return "\n".join(text_parts)
    except Exception as e:
        raise Exception(f"Failed to extract DOCX: {str(e)}")


def extract_document_text(file_object: Any) -> Dict[str, Any]:
    """
    Extract text from uploaded files using Gemini File API (in-memory processing).

    NO LOCAL FILE STORAGE - Everything stays in memory for Streamlit compatibility.
    Gemini files are deleted immediately after extraction.

    Args:
        file_object: Streamlit UploadedFile object (from st.file_uploader)

    Returns:
        Dictionary with:
        - status: 'success' or 'failed'
        - text: Extracted text content (if success)
        - error: Error message (if failed)
        - filename: Original filename
        - document_type: Classification (if detected)
    """
    try:
        # Extract metadata from UploadedFile
        filename = file_object.name
        file_ext = Path(filename).suffix.lower()
        file_size_mb = file_object.size / (1024 * 1024)

        # Validate file size
        if file_size_mb > FILE_UPLOAD_MAX_SIZE_MB:
            return {
                'status': 'failed',
                'error': f'File too large: {file_size_mb:.1f}MB (max {FILE_UPLOAD_MAX_SIZE_MB}MB)',
                'filename': filename
            }

        # Validate file extension
        if file_ext not in SUPPORTED_FILE_EXTENSIONS:
            return {
                'status': 'failed',
                'error': f'Unsupported file type: {file_ext}',
                'filename': filename
            }

        # Handle TXT files directly (in-memory)
        if file_ext == '.txt':
            try:
                text_content = file_object.read().decode('utf-8', errors='ignore')
                return {
                    'status': 'success',
                    'text': text_content,
                    'filename': filename,
                    'document_type': 'Other'
                }
            except Exception as e:
                return {
                    'status': 'failed',
                    'error': f'Failed to read text file: {str(e)}',
                    'filename': filename
                }

        # Handle DOCX files directly using python-docx (in-memory)
        if file_ext == '.docx':
            try:
                # Read bytes into BytesIO for python-docx
                from io import BytesIO
                file_bytes = BytesIO(file_object.read())
                doc = Document(file_bytes)

                text_parts = []
                for paragraph in doc.paragraphs:
                    if paragraph.text.strip():
                        text_parts.append(paragraph.text)

                # Extract from tables
                for table in doc.tables:
                    for row in table.rows:
                        row_text = []
                        for cell in row.cells:
                            row_text.append(cell.text)
                        if any(row_text):
                            text_parts.append(" | ".join(row_text))

                text_content = "\n".join(text_parts)

                if not text_content.strip():
                    return {
                        'status': 'failed',
                        'error': 'No text could be extracted from DOCX',
                        'filename': filename
                    }

                return {
                    'status': 'success',
                    'text': text_content,
                    'filename': filename,
                    'document_type': 'Other'
                }
            except Exception as e:
                return {
                    'status': 'failed',
                    'error': f'DOCX extraction error: {str(e)}',
                    'filename': filename
                }

        # For other file types (PDF, XLSX, PPTX, images), use Gemini File API
        # Process entirely in memory - create temp file only for upload
        gemini_file = None
        try:
            with st.spinner(f"📤 Processing {filename}..."):
                # Create TEMPORARY file in memory for Gemini upload
                with tempfile.NamedTemporaryFile(delete=True, suffix=file_ext) as tmp:
                    # Write file content
                    tmp.write(file_object.read())
                    tmp.flush()

                    # Upload to Gemini File API
                    gemini_file = client.files.upload(file=str(tmp.name))

            # Extract text using Gemini
            with st.spinner(f"🤖 Extracting text from {filename}..."):
                model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

                prompt = """Extract ALL text content from this document AND classify its type.

Instructions for extraction:
- Extract all readable text, preserving structure where possible
- Include headings, paragraphs, lists, and table content
- Maintain logical flow and organization
- Do not add commentary or interpretation

Classification:
- Classify document as ONE of: "RFP" (Request for Proposal/tender), "Meeting Notes" (discussion/call notes), or "Other"

Output format:
[DOCUMENT_TYPE]
<type: RFP, Meeting Notes, or Other>
[/DOCUMENT_TYPE]

[EXTRACTED_TEXT]
<complete text content here>
[/EXTRACTED_TEXT]"""

                response = client.models.generate_content(
                    model=model_name,
                    contents=[prompt, gemini_file]
                )

                response_text = response.text if response and hasattr(response, 'text') else ""

                # Parse document type and text from response
                document_type = "Other"
                extracted_text = ""

                try:
                    # Extract document type
                    if "[DOCUMENT_TYPE]" in response_text and "[/DOCUMENT_TYPE]" in response_text:
                        type_section = response_text.split("[DOCUMENT_TYPE]")[1].split("[/DOCUMENT_TYPE]")[0].strip()
                        if "RFP" in type_section and "Meeting" not in type_section:
                            document_type = "RFP"
                        elif "Meeting Notes" in type_section or "Meeting" in type_section:
                            document_type = "Meeting Notes"
                        elif "Other" in type_section:
                            document_type = "Other"
                        else:
                            if type_section in ["RFP", "Meeting Notes", "Other"]:
                                document_type = type_section

                    # Extract text
                    if "[EXTRACTED_TEXT]" in response_text and "[/EXTRACTED_TEXT]" in response_text:
                        extracted_text = response_text.split("[EXTRACTED_TEXT]")[1].split("[/EXTRACTED_TEXT]")[0].strip()
                    else:
                        extracted_text = response_text

                except Exception as e:
                    st.warning(f"Error parsing response: {e}")
                    extracted_text = response_text
                    document_type = None

                # If document type detection failed, use auto-detection
                if document_type is None and extracted_text:
                    document_type = detect_document_type(extracted_text)

                if not extracted_text.strip():
                    return {
                        'status': 'failed',
                        'error': 'No text could be extracted from the document',
                        'filename': filename
                    }

                return {
                    'status': 'success',
                    'text': extracted_text,
                    'filename': filename,
                    'document_type': document_type
                }

        finally:
            # CRITICAL: Always delete Gemini file immediately after use
            if gemini_file:
                try:
                    client.files.delete(name=gemini_file.name)
                except Exception as e:
                    st.warning(f"Failed to cleanup Gemini file: {e}")

    except Exception as e:
        return {
            'status': 'failed',
            'error': f'Extraction error: {str(e)}',
            'filename': filename if 'filename' in locals() else 'unknown'
        }


