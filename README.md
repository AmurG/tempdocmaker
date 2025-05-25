# docmaker-minimal: Automated Technical Documentation Generator

This project is an automated system for generating comprehensive technical documentation for a C++ codebase (specifically, the included `src/` example related to TritonCTS, a clock tree synthesis tool). It leverages Large Language Models (Anthropic Claude and Google Gemini) and program analysis tools (LlamaIndex for RAG, tree-sitter for code parsing) to produce a multi-layered set of Markdown documents.

The system performs the following key steps:

1.  **RAG Index Creation**: Builds a Retrieval Augmented Generation (RAG) index from PDF documents provided in the `metadata/` directory to add contextual information to the code.
2.  **Per-File Annotation**: Generates detailed Markdown notes for each source file in `src/`, augmenting these notes with relevant information from the RAG index.
3.  **Repository Analysis**: Uses `tree-sitter` to parse the C++ code, extracting structural information like includes, functions, and classes for each file.
4.  **Intermediate Documentation**: Creates combined documentation for related files (e.g., `.h` and `.cpp` pairs) and summaries for standalone modules, synthesizing information from the per-file notes and structural analysis.
5.  **High-Level Overview**: Generates a comprehensive project overview document by consolidating all previously generated notes and analyses.
6.  **Final Manual Generation**: Uses the Google Gemini API to:
    *   Generate a detailed Table of Contents (ToC) based on the high-level overview.
    *   Generate individual Markdown documents for each section specified in the ToC, written in a dry, technical engineering style.

## Project Structure

```
.
├── src/                  # Example C++ source code to be documented
├── metadata/             # PDF documents for RAG context
├── .env.example          # Example for API key configuration
├── .gitignore            # Specifies intentionally untracked files
├── requirements.txt      # Python dependencies
├── build_rag_index.py    # Script for Step 1
├── annotate_files.py     # Script for Step 2
├── analyze_repo.py       # Script for Step 3
├── generate_interdocs.py # Script for Step 4
├── generate_high_level_doc.py # Script for Step 5
├── generate_final_docs_gemini.py # Script for Step 6
└── README.md             # This file
```

**Generated Output Directories (created during runtime, excluded by `.gitignore`):**
*   `docenv/`: Python virtual environment.
*   `rag_index/`: Stores the LlamaIndex RAG index.
*   `file_notes/`: Contains Markdown notes for each source file.
*   `repo_structure.json`: JSON output of the tree-sitter analysis.
*   `intermediate_docs/`: Markdown documents linking related files/modules.
*   `high-level-overview/`: Contains `project_overview.md` and `TABLE_OF_CONTENTS.md`.
*   `final_documentation/`: Contains the final, Gemini-generated manual sections.

## Setup and Usage

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd docmaker-minimal
    ```

2.  **Create and activate a Python virtual environment:**
    ```bash
    python3 -m venv docenv
    source docenv/bin/activate  # On Windows: docenv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Set up API Keys:**
    Copy `.env.example` to `.env` (this file is gitignored):
    ```bash
    cp .env.example .env
    ```
    Then, edit `.env` and add your API keys:
    ```env
    ANTHROPIC_API_KEY="your_anthropic_api_key_here"
    GOOGLE_API_KEY="your_google_api_key_here" 
    # Note: The scripts also check for GEMINI_API_KEY if GOOGLE_API_KEY is not found.
    ```

5.  **Run the documentation generation pipeline:**
    Execute the scripts in the following order:
    ```bash
    python3 build_rag_index.py
    python3 annotate_files.py
    python3 analyze_repo.py
    python3 generate_interdocs.py
    python3 generate_high_level_doc.py
    python3 generate_final_docs_gemini.py
    ```
    This process can take a significant amount of time due to multiple LLM API calls and file processing.

6.  **View the results:**
    *   The primary high-level overview is in `high-level-overview/project_overview.md`.
    *   The generated Table of Contents is in `high-level-overview/TABLE_OF_CONTENTS.md`.
    *   The final, detailed manual sections are in the `final_documentation/` directory.
    *   Intermediate artifacts can be found in `file_notes/`, `intermediate_docs/`, and `repo_structure.json`.

## Requirements

*   Python 3.8+
*   Access to Anthropic API (for Claude models)
*   Access to Google AI API (for Gemini models)
*   A C compiler (for `tree-sitter` to build grammars if `tree-sitter-language-pack` fails or is not used, though the current setup uses pre-compiled grammars from the pack).

## Note on LLM Usage

This project makes extensive use of LLMs. Ensure you are aware of the associated costs and rate limits for the Anthropic and Google Gemini APIs. The scripts include basic retry mechanisms for API calls but may require adjustments based on your specific API plan and usage patterns. 