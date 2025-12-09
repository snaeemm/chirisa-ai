#!/usr/bin/env python3
"""Quick test script to verify Gemini API key and model availability."""

import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Get API key
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    print("❌ Error: GEMINI_API_KEY not found in environment")
    exit(1)

print(f"✓ API Key found: {api_key[:20]}...")

# Configure Gemini
genai.configure(api_key=api_key)

# Test models to try
models_to_test = [
    "gemini-3-flash-preview",
    "gemini-2.5-flash-preview-09-2025",
    "gemini-2.5-flash",
    "gemini-1.5-flash"
]

print("\n" + "="*60)
print("Testing Gemini Models")
print("="*60)

for model_name in models_to_test:
    try:
        print(f"\n🔍 Testing: {model_name}")
        model = genai.GenerativeModel(model_name)

        # Simple test prompt
        response = model.generate_content("Say 'Hello, I am working!' in exactly 5 words.")

        print(f"✅ SUCCESS: {model_name}")
        print(f"Response: {response.text.strip()}")

    except Exception as e:
        print(f"❌ FAILED: {model_name}")
        print(f"Error: {str(e)}")

print("\n" + "="*60)
print("Test Complete")
print("="*60)
