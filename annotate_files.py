import os
import anthropic
from llama_index.core import load_index_from_storage, StorageContext
# from llama_index.core.settings import Settings # Not strictly needed if defaults are fine
from dotenv import load_dotenv

# Load environment variables (ANTHROPIC_API_KEY, GOOGLE_API_KEY for LlamaIndex if needed)
load_dotenv()

# --- Configuration ---
ANTHROPIC_MODEL_NAME = "claude-3-5-sonnet-20240620"
MAX_TOKENS_NOTES = 4000  # Max tokens for initial notes
MAX_TOKENS_ADDENDUM = 1000 # Max tokens for the RAG addendum
SRC_DIR = "./src"
FILE_NOTES_DIR = "./file_notes"
RAG_INDEX_DIR = "./rag_index"
VALID_EXTENSIONS = {".h", ".cpp", ".i"}

# Initialize Anthropic client
# The API key will be picked up from ANTHROPIC_API_KEY environment variable
try:
    anthropic_client = anthropic.Anthropic()
except Exception as e:
    print(f"Failed to initialize Anthropic client: {e}")
    print("Please ensure ANTHROPIC_API_KEY is set in your .env file and is correct.")
    exit(1)

# --- Helper Functions ---

def get_anthropic_completion(prompt_text, max_tokens, model_name):
    try:
        response = anthropic_client.messages.create(
            model=model_name,
            max_tokens=max_tokens,
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
        print(f"Anthropic API returned an error (model: {model_name}, status: {e.status_code}): {e.message}")
        if e.status_code == 401: # Unauthorized
             print("Please check your ANTHROPIC_API_KEY.")
        elif e.status_code == 404: # Not Found
            print(f"Model '{model_name}' might not be available or the API endpoint is incorrect.")
        return None
    except Exception as e:
        print(f"Error calling Anthropic API ({model_name}): {type(e).__name__} - {e}")
        return None

def generate_initial_notes(file_content, file_path):
    lines_of_code = len(file_content.splitlines())
    estimated_markdown_lines = max(10, lines_of_code // 10)

    prompt = f"""Please generate precise, detailed technical notes for the following code file: {file_path}.
The notes should be in Markdown format.
Aim to summarize such that you output approximately 1 line of markdown for every 10 lines of code, but prioritize clarity, accuracy, and completeness of the explanation. The target output is roughly {estimated_markdown_lines} lines of Markdown.
Focus on explaining the purpose, functionality, key components, and any complex logic within the code.
Avoid fluff and filler words. The output should be suitable for a dry engineering manual.

Here is the code:
```
{file_content}
```

Provide only the Markdown notes.
"""
    print(f"Generating initial notes for {file_path} using {ANTHROPIC_MODEL_NAME}...")
    return get_anthropic_completion(prompt, MAX_TOKENS_NOTES, ANTHROPIC_MODEL_NAME)

def query_rag_index(query_text, index):
    print(f"Querying RAG index with text starting: '{query_text[:100].replace(os.linesep, ' ')}...'")
    query_engine = index.as_query_engine(similarity_top_k=3)
    try:
        response = query_engine.query(query_text)
        retrieved_texts = [node.get_content() for node in response.source_nodes]
        if retrieved_texts:
            print(f"Retrieved {len(retrieved_texts)} node(s) from RAG index.")
            return "\\n\\n---\\n\\n".join(retrieved_texts)
        else:
            print("No relevant nodes found in RAG index for this query.")
            return None
    except Exception as e:
        print(f"Error querying RAG index: {e}")
        return None

def generate_rag_addendum(original_notes, rag_retrieval, file_path):
    prompt = f"""You are tasked with creating a concise addendum to existing technical notes for the code file: {file_path}.
You have been provided with:
1. The original notes generated solely from the code.
2. Context retrieved from a RAG system (documentation PDFs).

Your goal is to synthesize information from the RAG retrieval that provides *additional, relevant context or clarification* to the original notes.
The addendum should be 10-20 lines of Markdown.
If the RAG retrieval does not offer significant new insights or is irrelevant to the code, output only the exact phrase "NO_ADDENDUM_NEEDED" and nothing else.
Do not repeat information already clear from the original notes. Focus on what the RAG context *adds*.

Original Notes:
---
{original_notes}
---

RAG Retrieved Context:
---
{rag_retrieval}
---

Based on the RAG context, generate a focused addendum (10-20 lines of Markdown). If no valuable addendum can be made, output only the exact phrase "NO_ADDENDUM_NEEDED".
"""
    print(f"Generating RAG addendum for {file_path} using {ANTHROPIC_MODEL_NAME}...")
    addendum_text = get_anthropic_completion(prompt, MAX_TOKENS_ADDENDUM, ANTHROPIC_MODEL_NAME)
    if addendum_text and "NO_ADDENDUM_NEEDED" in addendum_text.strip():
        return None
    return addendum_text

# --- Main Logic ---
def main():
    if not os.path.exists(SRC_DIR):
        print(f"Source directory '{SRC_DIR}' not found.")
        return
    if not os.path.exists(FILE_NOTES_DIR):
        print(f"File notes directory '{FILE_NOTES_DIR}' not found. Please create it or ensure it exists.")
        return
    if not os.path.exists(RAG_INDEX_DIR):
        print(f"RAG index directory '{RAG_INDEX_DIR}' not found. Please run build_rag_index.py first.")
        return

    print("Loading RAG index...")
    try:
        storage_context = StorageContext.from_defaults(persist_dir=RAG_INDEX_DIR)
        index = load_index_from_storage(storage_context)
        print("RAG index loaded successfully.")
    except Exception as e:
        print(f"Failed to load RAG index: {e}")
        return

    processed_files = 0
    for root, _, files in os.walk(SRC_DIR):
        for filename in files:
            if any(filename.endswith(ext) for ext in VALID_EXTENSIONS):
                file_path = os.path.join(root, filename)
                output_md_filename = filename + ".md"
                output_md_path = os.path.join(FILE_NOTES_DIR, output_md_filename)

                if os.path.exists(output_md_path):
                    print(f"Notes for {file_path} already exist at {output_md_path}. Skipping.")
                    continue

                print(f"\\nProcessing file: {file_path}")
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                except Exception as e:
                    print(f"Error reading file {file_path}: {e}")
                    continue

                if not content.strip():
                    print(f"File {file_path} is empty. Skipping.")
                    continue
                
                initial_notes = generate_initial_notes(content, file_path)
                if not initial_notes:
                    print(f"Failed to generate initial notes for {file_path}. Skipping.")
                    continue

                # Query RAG with the first 5000 chars to avoid overly long/costly queries.
                # Anthropic's context window for Sonnet 3.5 is large (200K), but RAG queries are often better shorter.
                rag_query_content = content[:5000] 
                rag_retrieval = query_rag_index(rag_query_content, index)
                
                final_notes = initial_notes
                if rag_retrieval:
                    addendum = generate_rag_addendum(initial_notes, rag_retrieval, file_path)
                    if addendum:
                        final_notes += "\\n\\n## RAG Addendum\\n" + addendum
                        print(f"RAG addendum added for {file_path}.")
                    else:
                        print(f"No RAG addendum deemed necessary or generated for {file_path}.")
                else:
                    print(f"No relevant information found in RAG index to generate an addendum for {file_path}.")

                try:
                    with open(output_md_path, 'w', encoding='utf-8') as f:
                        f.write(final_notes)
                    print(f"Successfully saved notes to {output_md_path}")
                    processed_files += 1
                except Exception as e:
                    print(f"Error writing notes to {output_md_path}: {e}")

    print(f"\\nAnnotation process completed. Processed {processed_files} new files.")

if __name__ == "__main__":
    main() 