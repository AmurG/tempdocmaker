#!/bin/bash
# This script runs the full docmaker-minimal documentation pipeline.
# It should be executed from the root of the project repository.

set -e

echo "--- DocMaker Pipeline Starting ---"

# Ensure the virtual environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Warning: Python virtual environment not detected. Assuming dependencies are globally installed."
    PYTHON_CMD="python3"
else
    PYTHON_CMD="python"
fi

# Step 1: Build RAG Index
echo "\\n--- Step 1: Building RAG Index ---"
$PYTHON_CMD build_rag_index.py

# Step 2: Annotate Source Files
echo "\\n--- Step 2: Annotating Source Files ---"
$PYTHON_CMD annotate_files.py

# Step 3: Analyze Repository Structure
echo "\\n--- Step 3: Analyzing Repository Structure ---"
$PYTHON_CMD analyze_repo.py

# Step 4: Generate Intermediate Documentation
echo "\\n--- Step 4: Generating Intermediate Documentation ---"
$PYTHON_CMD generate_interdocs.py

# Step 5: Generate High-Level Overview
echo "\\n--- Step 5: Generating High-Level Overview ---"
$PYTHON_CMD generate_high_level_doc.py

# Step 6: Generate Final Documentation with Gemini
echo "\\n--- Step 6: Generating Final Documentation with Gemini ---"
$PYTHON_CMD generate_final_docs_gemini.py

echo "\\n--- DocMaker Pipeline Completed Successfully ---" 