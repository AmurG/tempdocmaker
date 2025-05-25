import os
import google.generativeai as genai
from dotenv import load_dotenv
import re
import time

load_dotenv()

# --- Configuration ---
GEMINI_MODEL_NAME = "gemini-1.5-flash-latest" 
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY: # Fallback to GEMINI_API_KEY
    print("GOOGLE_API_KEY not found, trying GEMINI_API_KEY...")
    GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")

HIGH_LEVEL_OVERVIEW_DIR = "./high-level-overview"
PROJECT_OVERVIEW_FILE = os.path.join(HIGH_LEVEL_OVERVIEW_DIR, "project_overview.md")
TOC_FILE = os.path.join(HIGH_LEVEL_OVERVIEW_DIR, "TABLE_OF_CONTENTS.md")
FINAL_DOCS_OUTPUT_DIR = "./final_documentation" 

# Gemini API safety settings - adjust as needed
SAFETY_SETTINGS = [
    {
        "category": "HARM_CATEGORY_HARASSMENT",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_HATE_SPEECH",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
        "threshold": "BLOCK_NONE",
    },
    {
        "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
        "threshold": "BLOCK_NONE",
    },
]
# Generation config - e.g., temperature for creativity, max_output_tokens for length
GENERATION_CONFIG = {
    "temperature": 0.2, # Lower for more factual, less creative
    "max_output_tokens": 8192, # Max for Gemini 1.5 Flash
}


# --- Initialize Gemini Client ---
if not GOOGLE_API_KEY:
    print("Error: GOOGLE_API_KEY not found in .env file.")
    exit(1)

genai.configure(api_key=GOOGLE_API_KEY)
# Initialize the model with safety settings and generation config
gemini_model = genai.GenerativeModel(
    GEMINI_MODEL_NAME,
    safety_settings=SAFETY_SETTINGS,
    generation_config=GENERATION_CONFIG
)

# --- Helper Functions ---
def get_gemini_completion(prompt_text):
    print(f"Sending prompt to Gemini ({GEMINI_MODEL_NAME}). Prompt length (chars): {len(prompt_text)}")
    max_retries = 3
    retry_delay_seconds = 10 # More for quota errors
    for attempt in range(max_retries):
        try:
            response = gemini_model.generate_content(prompt_text)
            
            if response.parts:
                full_text = "".join([part.text for part in response.parts if hasattr(part, 'text')])
                if full_text:
                    print(f"Received completion from Gemini. Output length (chars): {len(full_text)}")
                    # Check for blockages despite text
                    if response.prompt_feedback and response.prompt_feedback.block_reason:
                        print(f"Warning: Prompt feedback indicates blockage: {response.prompt_feedback.block_reason_message}")
                        # Continue with the text if available, but log warning
                    return full_text
            
            # If no parts or no text in parts, check for explicit block reason
            if response.prompt_feedback and response.prompt_feedback.block_reason:
                 print(f"Gemini API request failed: Prompt blocked. Reason: {response.prompt_feedback.block_reason_message}")
                 return None # Blocked content is a hard failure for this part
            
            # Fallback if structure is unexpected but not explicitly blocked
            print(f"Gemini API returned an empty or unexpected response structure. Response: {response}")
            return None # Or handle as error if appropriate

        except Exception as e:
            print(f"Error calling Gemini API ({GEMINI_MODEL_NAME}) on attempt {attempt + 1}: {type(e).__name__} - {e}")
            # Specific error handling for quota issues if possible (e.g. check e.status_code if it's an HTTPError)
            # For now, a generic retry for common transient issues.
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay_seconds} seconds...")
                time.sleep(retry_delay_seconds)
                retry_delay_seconds *= 2 # Exponential backoff for retries
            else:
                print("Max retries reached.")
                return None
    return None # Should be unreachable if loop logic is correct

def load_file_content(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return None

def sanitize_filename(title):
    title = re.sub(r'^\s*#+\s*', '', title)
    title = title.strip().replace(' ', '_').replace('/', '-').replace('\\', '-')
    title = re.sub(r'[^\w\-\_\.]', '', title)
    title = re.sub(r'\.+$', '', title) # Remove trailing dots
    if not title: title = "untitled_section"
    return title[:100] + ".md"

def parse_toc_markdown(toc_content):
    sections = []
    # Match H1, H2, or H3 as potential main sections/parts. Capture the title part.
    # This regex tries to capture titles like "# 1. Introduction", "## Section A", "### Subsection 1.1"
    # It strips leading/trailing whitespace from the captured title.
    header_pattern = re.compile(r"^\s*(#{1,3})\s+([^#\n]+)")
    for line in toc_content.splitlines():
        match = header_pattern.match(line)
        if match:
            title = match.group(2).strip() # Get the text part of the header
            # Further clean title: remove potential numbering like "1. ", "A. "
            title = re.sub(r"^\s*\d+\.\s*|^\s*[A-Za-z]\.\s*", "", title).strip()
            if title:
                sections.append(title)
    
    if not sections: # Fallback for simple list items if no headers found
        print("No H1/H2/H3 headers found in ToC, trying to parse list items...")
        list_item_pattern = re.compile(r"^\s*[*\-]\s+(.+)")
        for line in toc_content.splitlines():
            match = list_item_pattern.match(line)
            if match:
                title = match.group(1).strip()
                title = re.sub(r"^\s*\d+\.\s*|^\s*[A-Za-z]\.\s*", "", title).strip()
                if title:
                    sections.append(title)
    print(f"Parsed ToC. Found {len(sections)} sections: {sections}")
    return sections

# --- Main Logic ---
def main():
    project_overview_content = load_file_content(PROJECT_OVERVIEW_FILE)
    if not project_overview_content:
        print("Exiting: Project overview content not loaded.")
        return

    if not os.path.exists(FINAL_DOCS_OUTPUT_DIR):
        os.makedirs(FINAL_DOCS_OUTPUT_DIR)
        print(f"Created directory: {FINAL_DOCS_OUTPUT_DIR}")

    # 1. Generate Table of Contents
    print("\n--- Generating Table of Contents ---")
    toc_prompt = f"""Based on the following project overview, generate a detailed Table of Contents (ToC) for a comprehensive technical manual.
This technical manual is for a C++ software project related to clock tree synthesis (CTS), likely named TritonCTS or similar.
The manual should be structured into logical parts and sections (e.g., using H1 for parts, H2 for main sections within parts, and H3 for sub-sections if appropriate).
Each major H2 section described in the ToC should eventually correspond to content of approximately 1000-1500 words.
Output the Table of Contents ONLY in Markdown format. Ensure section titles are descriptive and suitable for a technical audience.

Project Overview:
{project_overview_content}

---
Generate the Markdown Table of Contents. Do not include any introductory or concluding remarks, only the ToC itself.
"""
    toc_markdown = get_gemini_completion(toc_prompt)

    if toc_markdown:
        try:
            with open(TOC_FILE, 'w', encoding='utf-8') as f:
                f.write(toc_markdown)
            print(f"Table of Contents saved to {TOC_FILE}")
        except Exception as e:
            print(f"Error writing ToC to {TOC_FILE}: {e}")
            print("Proceeding without saving ToC, but section generation might fail or use a stale ToC.")
    else:
        print("Failed to generate Table of Contents. Attempting to load existing ToC if available.")
        if os.path.exists(TOC_FILE):
            print(f"Loading existing ToC from {TOC_FILE}")
            toc_markdown = load_file_content(TOC_FILE)
            if not toc_markdown:
                print("Failed to load existing ToC. Cannot proceed.")
                return
        else:
            print("No existing ToC found. Cannot proceed.")
            return

    # 2. Parse ToC and generate content for each section
    print("\n--- Generating Content for Each Section from ToC ---")
    sections_to_generate = parse_toc_markdown(toc_markdown)
    
    if not sections_to_generate:
        print("No sections found in the ToC. Cannot generate individual documents.")
        return

    total_sections = len(sections_to_generate)
    for i, section_title in enumerate(sections_to_generate):
        print(f"\n--- Generating content for section {i+1}/{total_sections}: '{section_title}' ---")
        section_filename = sanitize_filename(section_title)
        section_output_path = os.path.join(FINAL_DOCS_OUTPUT_DIR, section_filename)

        if os.path.exists(section_output_path):
            print(f"Skipping section '{section_title}', output file already exists: {section_output_path}")
            continue

        section_prompt = f"""You are writing a section titled '{section_title}' for a technical manual about a C++ Clock Tree Synthesis (CTS) software project (likely TritonCTS).
The overall project context is provided by the project overview below.
The complete Table of Contents for the manual is also provided for context on where this section fits.

Project Overview:
{project_overview_content}

Complete Table of Contents:
{toc_markdown}

Your task is to generate ONLY the Markdown content for the section titled: '{section_title}'

Guidelines for this section:
- Content should be highly detailed, technically accurate, and comprehensive for this specific topic.
- Adhere to a dry, rigorous, and professional engineering manual style. Avoid conversational language, fluff, or filler words.
- The target audience is engineers who will use or develop this software.
- Aim for a word count appropriate for a significant manual section (e.g., 1000-1500 words, or what naturally fits the topic depth). Use subheadings (H3, H4, etc.) within this section as needed for structure.
- Start your output directly with the content for this section. Do NOT repeat the section title '{section_title}' as a top-level H1 or H2 header if it is already implied as the main topic of this generation; focus on the substance.
- Ensure the information is consistent with the provided project overview and its place in the ToC.

Section Content for '{section_title}':
"""
        section_content = get_gemini_completion(section_prompt)

        if section_content:
            try:
                with open(section_output_path, 'w', encoding='utf-8') as f:
                    f.write(section_content)
                print(f"Content for section '{section_title}' saved to {section_output_path}")
            except Exception as e:
                print(f"Error writing section '{section_title}' to {section_output_path}: {e}")
        else:
            print(f"Failed to generate content for section '{section_title}'. Moving to next section.")
            
    print("\n--- Final documentation generation process completed using Gemini API ---")

if __name__ == "__main__":
    main() 