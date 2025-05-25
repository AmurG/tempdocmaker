import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
ANTHROPIC_MODEL_NAME = "claude-3-5-sonnet-20240620"
# Increased max tokens for this more demanding summarization task
# Claude 3.5 Sonnet has a 200K context window. We want to allow a large output.
MAX_TOKENS_HLD = 8000 # Max tokens for the high-level overview itself (max for model is 8192)
MAX_PROMPT_CHARS_APPROX = 180000 * 3 # Approx char limit for prompt (e.g. ~50-60k tokens for Claude Sonnet 3.5)

FILE_NOTES_DIR = "./file_notes"
INTERMEDIATE_DOCS_DIR = "./intermediate_docs"
HIGH_LEVEL_OVERVIEW_DIR = "./high-level-overview"
REPO_STRUCTURE_FILE = "./repo_structure.json"

try:
    anthropic_client = anthropic.Anthropic()
except Exception as e:
    print(f"Failed to initialize Anthropic client: {e}. Ensure ANTHROPIC_API_KEY is set.")
    exit(1)

# --- Helper Functions ---
def get_anthropic_completion(prompt_text, max_tokens=MAX_TOKENS_HLD):
    print(f"Sending prompt to Anthropic ({ANTHROPIC_MODEL_NAME}). Prompt length (chars): {len(prompt_text)}, Max new tokens: {max_tokens}")
    try:
        response = anthropic_client.messages.create(
            model=ANTHROPIC_MODEL_NAME,
            max_tokens=max_tokens, # Max tokens for the *output* a.k.a. completion
            messages=[
                {"role": "user", "content": prompt_text}
            ]
        )
        if response.content and isinstance(response.content, list) and \
           len(response.content) > 0 and hasattr(response.content[0], 'text'):
            completion_text = response.content[0].text
            print(f"Received completion from Anthropic. Output length (chars): {len(completion_text)}")
            return completion_text
        else:
            print(f"Unexpected response structure from Anthropic API: {response}")
            return None
    except anthropic.APIStatusError as e:
        print(f"Anthropic API returned an error (model: {ANTHROPIC_MODEL_NAME}, status: {e.status_code}): {e.message}")
        if hasattr(e, 'response') and hasattr(e.response, 'text'):
            print(f"Error details: {e.response.text}")
        return None
    except Exception as e:
        print(f"Error calling Anthropic API ({ANTHROPIC_MODEL_NAME}): {type(e).__name__} - {e}")
        return None

def load_all_markdown_from_dir(directory):
    all_md_content_list = []
    if not os.path.exists(directory):
        print(f"Warning: Directory {directory} not found for loading markdown.")
        return ""
    print(f"Loading all markdown from: {directory}")
    for filename in sorted(os.listdir(directory)): # Sorted for consistent order
        if filename.endswith(".md"):
            file_path = os.path.join(directory, filename)
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    all_md_content_list.append(f"\n\n--- Content from: {filename} ---\n{content}")
                    print(f"  Loaded: {filename} ({len(content)} chars)")
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
    return "".join(all_md_content_list) # Join with no extra separator, already in list items

def main():
    if not os.path.exists(HIGH_LEVEL_OVERVIEW_DIR):
        os.makedirs(HIGH_LEVEL_OVERVIEW_DIR)
        print(f"Created directory: {HIGH_LEVEL_OVERVIEW_DIR}")

    print("\nLoading data for high-level overview generation...")
    
    repo_structure_str = ""
    if os.path.exists(REPO_STRUCTURE_FILE):
        try:
            with open(REPO_STRUCTURE_FILE, 'r', encoding='utf-8') as f:
                # Load then dump to ensure consistent string formatting and for easy inclusion
                repo_structure_data = json.load(f)
                repo_structure_str = json.dumps(repo_structure_data, indent=2)
                print(f"Loaded repository structure: {REPO_STRUCTURE_FILE} ({len(repo_structure_str)} chars)")
        except Exception as e:
            print(f"Error reading {REPO_STRUCTURE_FILE}: {e}")
            repo_structure_str = "{}\nError loading repository structure." # Placeholder on error
    else:
        print(f"Warning: {REPO_STRUCTURE_FILE} not found.")
        repo_structure_str = "Repository structure file not found."

    file_notes_content = load_all_markdown_from_dir(FILE_NOTES_DIR)
    intermediate_docs_content = load_all_markdown_from_dir(INTERMEDIATE_DOCS_DIR)
    
    # Construct the prompt, being mindful of token limits
    # The order is: structure, then intermediate (more summarized), then raw file notes (most verbose)
    # This puts more summarized info first if truncation happens.
    prompt_sections = [
        f"## Repository Structure:\n```json\n{repo_structure_str}\n```",
        "## Intermediate Component Documentation:",
        intermediate_docs_content,
        "## Detailed Per-File Notes:",
        file_notes_content
    ]

    combined_input_text = "\n\n".join(prompt_sections)
    
    current_chars = len(combined_input_text)
    if current_chars > MAX_PROMPT_CHARS_APPROX:
        print(f"Warning: Combined input text is very long ({current_chars} chars). Attempting to truncate intelligently.")
        # Simple truncation strategy: take all of structure, then as much of intermediate, then file notes.
        chars_left = MAX_PROMPT_CHARS_APPROX
        truncated_sections = []
        
        # Section 1: Repo Structure (always include fully if possible)
        section1_len = len(prompt_sections[0]) + len(prompt_sections[1]) + 4 # + separators
        if chars_left >= section1_len:
            truncated_sections.append(prompt_sections[0])
            truncated_sections.append(prompt_sections[1])
            chars_left -= section1_len
        else:
            print("Warning: Even repo structure is too long for truncation limit. Taking what fits.")
            truncated_sections.append(prompt_sections[0][:chars_left])
            chars_left = 0

        # Section 2: Intermediate Docs
        if chars_left > 0 and len(prompt_sections[2]) > 0:
            content_to_add = prompt_sections[2]
            if len(content_to_add) <= chars_left:
                truncated_sections.append(content_to_add)
                chars_left -= len(content_to_add) + 2 # + separator
            else:
                truncated_sections.append(content_to_add[:chars_left])
                chars_left = 0
        
        # Section 3: File Notes
        if chars_left > 0 and len(prompt_sections[3]) > 0 and len(prompt_sections[4]) > 0:
            truncated_sections.append(prompt_sections[3]) # The header for file notes
            chars_left -= (len(prompt_sections[3]) + 2)
            content_to_add = prompt_sections[4]
            if len(content_to_add) <= chars_left:
                truncated_sections.append(content_to_add)
            else:
                truncated_sections.append(content_to_add[:chars_left])
        
        combined_input_text = "\n\n".join(truncated_sections)
        print(f"Truncated input text to {len(combined_input_text)} chars.")

    prompt = f"""You are an AI assistant tasked with generating a high-level overview Markdown document for a C++ software project.
Your goal is to synthesize all provided information into a single, coherent high-level overview. This document should:
- Start with an introduction to the project's likely purpose and overall architecture.
- Describe the main components/modules and their primary responsibilities.
- Explain how these components generally interact, based on the structural information (like includes) and functional descriptions from the notes.
- Be structured logically with clear Markdown headings and subheadings (e.g., ## Introduction, ## Architecture Overview, ### Component X, ### Component Y, ## Data Structures, ## Key Algorithms, ## Dependencies, etc.).
- This overview will serve as the primary source material for later generating a detailed Table of Contents and section-by-section documentation for a complete technical manual.
- Maintain a dry, technical, and rigorous engineering tone. Be precise. Cut fluff and filler words.
- The project name seems to be related to "TritonCTS" or a similar system, likely for clock tree synthesis in electronic design.

Provided materials (potentially truncated if too long):
{combined_input_text}

---
Generate the comprehensive high-level overview in Markdown format. Ensure the output is well-structured and detailed enough to form the backbone of a technical manual.
"""

    print("\nGenerating high-level overview document (this may take a while)...")
    overview_content = get_anthropic_completion(prompt, max_tokens=MAX_TOKENS_HLD)

    if overview_content:
        output_path = os.path.join(HIGH_LEVEL_OVERVIEW_DIR, "project_overview.md")
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(overview_content)
            print(f"High-level overview saved to {output_path} ({len(overview_content)} chars)")
        except Exception as e:
            print(f"Error writing overview to {output_path}: {e}")
    else:
        print("Failed to generate high-level overview content from Anthropic.")

if __name__ == "__main__":
    main() 