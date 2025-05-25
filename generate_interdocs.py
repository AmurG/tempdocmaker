import os
import json
import anthropic
from dotenv import load_dotenv

load_dotenv()

# --- Configuration ---
ANTHROPIC_MODEL_NAME = "claude-3-5-sonnet-20240620"
MAX_TOKENS_INTERDOC = 4000 
SRC_DIR = "./src" # Used for relative path calculations
FILE_NOTES_DIR = "./file_notes"
INTERMEDIATE_DOCS_DIR = "./intermediate_docs"
REPO_STRUCTURE_FILE = "./repo_structure.json"
VALID_CPP_EXTENSIONS = {".h", ".cpp", ".i"}


try:
    anthropic_client = anthropic.Anthropic()
except Exception as e:
    print(f"Failed to initialize Anthropic client: {e}. Ensure ANTHROPIC_API_KEY is set.")
    exit(1)

# --- Helper Functions ---
def get_anthropic_completion(prompt_text):
    try:
        response = anthropic_client.messages.create(
            model=ANTHROPIC_MODEL_NAME,
            max_tokens=MAX_TOKENS_INTERDOC,
            messages=[
                {"role": "user", "content": prompt_text}
            ]
        )
        if response.content and isinstance(response.content, list) and \
           len(response.content) > 0 and hasattr(response.content[0], 'text'):
            return response.content[0].text
        else:
            print(f"Unexpected response structure from Anthropic API: {response}")
            return None
    except anthropic.APIStatusError as e:
        print(f"Anthropic API returned an error (model: {ANTHROPIC_MODEL_NAME}, status: {e.status_code}): {e.message}")
        return None
    except Exception as e:
        print(f"Error calling Anthropic API ({ANTHROPIC_MODEL_NAME}): {type(e).__name__} - {e}")
        return None

def load_json_data(file_path):
    if not os.path.exists(file_path):
        print(f"Error: File {file_path} not found.")
        return None
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error reading JSON from {file_path}: {e}")
        return None

def get_file_notes(filename_with_ext):
    md_path = os.path.join(FILE_NOTES_DIR, filename_with_ext + ".md")
    if os.path.exists(md_path):
        try:
            with open(md_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading notes from {md_path}: {e}")
    else:
        print(f"Note file not found: {md_path}")
    return None

def generate_combined_doc(header_file_path, cpp_file_path, header_notes, cpp_notes, header_struct, cpp_struct):
    prompt = f"""Generate an intermediate technical documentation page in Markdown for the following related C++ files:
Header File: {header_file_path}
Implementation File: {cpp_file_path}

Combined Goal: Briefly explain the overall purpose of this pair of files, how they relate (e.g., class declaration in .h, definition in .cpp), and summarize their key functionalities. Merge and synthesize the provided notes. Be technical and rigorous, avoid fluff.

Header File Notes:
---
{header_notes or "No notes available for header file."}
---

Header File Structure (from tree-sitter analysis):
Includes: {header_struct.get('includes', []) if header_struct else 'N/A'}
Functions: {header_struct.get('functions', []) if header_struct else 'N/A'}
Classes: {header_struct.get('classes', []) if header_struct else 'N/A'}
---

Implementation File Notes:
---
{cpp_notes or "No notes available for implementation file."}
---

Implementation File Structure (from tree-sitter analysis):
Includes: {cpp_struct.get('includes', []) if cpp_struct else 'N/A'}
Functions: {cpp_struct.get('functions', []) if cpp_struct else 'N/A'}
Classes: {cpp_struct.get('classes', []) if cpp_struct else 'N/A'} 
---

Produce a concise Markdown document for these combined files. Focus on their joint role and key aspects.
Output only the Markdown content.
"""
    print(f"Generating intermediate doc for {os.path.basename(header_file_path)} and {os.path.basename(cpp_file_path)}...")
    return get_anthropic_completion(prompt)

def generate_single_file_doc(file_path, notes, structure_info):
    prompt = f"""The following are notes and structural information for the C++ file: {file_path}

File Notes:
---
{notes or "No notes available for this file."}
---

File Structure (from tree-sitter analysis):
Includes: {structure_info.get('includes', [])}
Functions: {structure_info.get('functions', [])}
Classes: {structure_info.get('classes', [])}
---

Briefly summarize this file's role and key aspects based on the provided information, in Markdown format. Be technical and rigorous, avoid fluff.
This will serve as an intermediate documentation page for this single file.
Output only the Markdown content.
"""
    print(f"Generating intermediate doc for single file: {os.path.basename(file_path)}...")
    return get_anthropic_completion(prompt)

# --- Main Logic ---
def main():
    repo_structure = load_json_data(REPO_STRUCTURE_FILE)
    if not repo_structure:
        print("Exiting: Repo structure file not loaded.")
        return

    if not os.path.exists(INTERMEDIATE_DOCS_DIR):
        os.makedirs(INTERMEDIATE_DOCS_DIR)
        print(f"Created directory: {INTERMEDIATE_DOCS_DIR}")

    processed_files = set()
    generated_doc_count = 0

    # Strategy 1: Pair .h and .cpp files
    print("\nStarting Strategy 1: Pairing .h and .cpp files...")
    for file_path_key_in_struct, structure_info in repo_structure.items():
        if file_path_key_in_struct in processed_files:
            continue

        # file_path_key_in_struct is like './src/CtsOptions.h'
        # os.path.basename gives 'CtsOptions.h'
        original_filename = os.path.basename(file_path_key_in_struct)
        base_name_no_ext, ext = os.path.splitext(original_filename)

        if ext == ".h":
            # Try to find matching .cpp file based on path in repo_structure
            # The keys in repo_structure are like './src/FileName.ext'
            potential_cpp_key = os.path.join(os.path.dirname(file_path_key_in_struct), base_name_no_ext + ".cpp")
            
            if potential_cpp_key in repo_structure:
                cpp_file_path_key_in_struct = potential_cpp_key
                cpp_original_filename = os.path.basename(cpp_file_path_key_in_struct)

                print(f"Found pair: {original_filename} and {cpp_original_filename}")

                header_notes = get_file_notes(original_filename)
                cpp_notes = get_file_notes(cpp_original_filename)
                cpp_structure_info = repo_structure.get(cpp_file_path_key_in_struct)

                if header_notes is None and cpp_notes is None:
                    print(f"Skipping pair {original_filename}/{cpp_original_filename} due to missing notes for both.")
                    processed_files.add(file_path_key_in_struct)
                    processed_files.add(cpp_file_path_key_in_struct)
                    continue

                combined_doc_content = generate_combined_doc(
                    file_path_key_in_struct, cpp_file_path_key_in_struct,
                    header_notes, cpp_notes,
                    structure_info, cpp_structure_info
                )

                if combined_doc_content:
                    pair_doc_filename = base_name_no_ext + "_pair.md"
                    output_path = os.path.join(INTERMEDIATE_DOCS_DIR, pair_doc_filename)
                    try:
                        with open(output_path, 'w', encoding='utf-8') as f:
                            f.write(combined_doc_content)
                        print(f"Saved combined doc to {output_path}")
                        generated_doc_count += 1
                    except Exception as e:
                        print(f"Error writing combined doc {output_path}: {e}")
                else:
                    print(f"Failed to generate combined doc for {original_filename} and {cpp_original_filename}.")
                
                processed_files.add(file_path_key_in_struct)
                processed_files.add(cpp_file_path_key_in_struct)
    
    # Strategy 2: Process remaining standalone C++ files (.h, .cpp, .i) that weren't part of a pair
    print("\nStarting Strategy 2: Processing standalone C++ files...")
    for file_path_key_in_struct, structure_info in repo_structure.items():
        if file_path_key_in_struct in processed_files:
            continue
        
        original_filename = os.path.basename(file_path_key_in_struct)
        _, ext = os.path.splitext(original_filename)

        if ext in VALID_CPP_EXTENSIONS:
            notes = get_file_notes(original_filename)
            if not notes:
                print(f"Skipping standalone file {original_filename} due to missing notes.")
                processed_files.add(file_path_key_in_struct)
                continue
            
            single_doc_content = generate_single_file_doc(file_path_key_in_struct, notes, structure_info)
            if single_doc_content:
                single_doc_filename = original_filename + "_single.md"
                output_path = os.path.join(INTERMEDIATE_DOCS_DIR, single_doc_filename)
                try:
                    with open(output_path, 'w', encoding='utf-8') as f:
                        f.write(single_doc_content)
                    print(f"Saved single file doc to {output_path}")
                    generated_doc_count += 1
                except Exception as e:
                    print(f"Error writing single file doc {output_path}: {e}")
            else:
                print(f"Failed to generate single doc for {original_filename}.")
            processed_files.add(file_path_key_in_struct)
    
    print(f"\nIntermediate documentation generation process completed. Generated {generated_doc_count} documents.")

if __name__ == "__main__":
    main() 