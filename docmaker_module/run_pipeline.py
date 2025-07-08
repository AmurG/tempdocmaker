import os
import json
import time
import re
import argparse
import anthropic
import google.generativeai as genai
from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, load_index_from_storage, StorageContext
from tree_sitter_language_pack import get_language, get_parser
from tree_sitter import Parser

# --- Initial Setup ---
load_dotenv()
print("--- DocMaker Pipeline Initializing ---")

# --- Global Configurations & Clients ---
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")

ANTHROPIC_MODEL_NAME = "claude-3-5-sonnet-20240620"
GEMINI_MODEL_NAME = "gemini-1.5-flash-latest"

anthropic_client = None
gemini_model = None

# --- Models and API Helpers ---
def init_anthropic_client():
    global anthropic_client
    if not ANTHROPIC_API_KEY:
        print("Error: ANTHROPIC_API_KEY not found.")
        return False
    try:
        anthropic_client = anthropic.Anthropic()
        print("Anthropic client initialized.")
        return True
    except Exception as e:
        print(f"Failed to initialize Anthropic client: {e}")
        return False

def init_gemini_client():
    global gemini_model
    if not GOOGLE_API_KEY:
        print("Error: GOOGLE_API_KEY (or GEMINI_API_KEY) not found.")
        return False
    try:
        genai.configure(api_key=GOOGLE_API_KEY)
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]
        generation_config = {"temperature": 0.2, "max_output_tokens": 8192}
        gemini_model = genai.GenerativeModel(GEMINI_MODEL_NAME, safety_settings=safety_settings, generation_config=generation_config)
        print("Gemini client initialized.")
        return True
    except Exception as e:
        print(f"Failed to initialize Gemini client: {e}")
        return False

def get_anthropic_completion(prompt_text, max_tokens):
    # ... (Full implementation of get_anthropic_completion)
    pass

def get_gemini_completion(prompt_text):
    # ... (Full implementation of get_gemini_completion)
    pass

# --- Pipeline Step Functions ---
def step_1_build_rag_index(metadata_dir, index_dir):
    print("\n--- Step 1: Building RAG Index ---")
    # ... (Full implementation from build_rag_index.py)
    pass

def step_2_annotate_files(src_dir, notes_dir, index_dir):
    print("\n--- Step 2: Annotating Source Files ---")
    # ... (Full implementation from annotate_files.py)
    pass

def step_3_analyze_repo(src_dir, output_json):
    print("\n--- Step 3: Analyzing Repository Structure ---")
    # ... (Full implementation from analyze_repo.py)
    pass

def step_4_generate_interdocs(repo_structure_file, notes_dir, inter_docs_dir, src_dir):
    print("\n--- Step 4: Generating Intermediate Docs ---")
    # ... (Full implementation from generate_interdocs.py)
    pass

def step_5_generate_high_level_doc(notes_dir, inter_docs_dir, repo_structure_file, overview_dir):
    print("\n--- Step 5: Generating High-Level Overview ---")
    # ... (Full implementation from generate_high_level_doc.py)
    pass

def step_6_generate_final_docs(overview_dir, final_docs_dir):
    print("\n--- Step 6: Generating Final Documentation with Gemini ---")
    # ... (Full implementation from generate_final_docs_gemini.py)
    pass

# --- Main Execution Block ---
def main():
    parser = argparse.ArgumentParser(description="Run the full docmaker-minimal documentation pipeline.")
    # Add arguments for all directories...
    args = parser.parse_args()
    
    # Initialize clients
    if not init_anthropic_client() or not init_gemini_client():
        print("Failed to initialize API clients. Exiting.")
        return
        
    # Execute steps
    step_1_build_rag_index(args.metadata_dir, args.index_dir)
    step_2_annotate_files(args.src_dir, args.notes_dir, args.index_dir)
    step_3_analyze_repo(args.src_dir, args.repo_structure_json)
    step_4_generate_interdocs(args.repo_structure_file, args.notes_dir, args.inter_docs_dir, args.src_dir)
    step_5_generate_high_level_doc(args.notes_dir, args.inter_docs_dir, args.repo_structure_file, args.overview_dir)
    step_6_generate_final_docs(args.overview_dir, args.final_docs_dir)

if __name__ == "__main__":
    main() 