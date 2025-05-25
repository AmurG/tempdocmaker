import os
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from dotenv import load_dotenv

# Load API keys from .env file
load_dotenv()

# Ensure API keys are loaded (LlamaIndex might need them for embedding models)
# For example, if using OpenAI embeddings by default:
# os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY") 
# If using a different embedding model that needs a key, ensure it's set.
# For now, we assume LlamaIndex will use a default or an appropriately configured model.
# We also need to explicitly set the GOOGLE_API_KEY for Gemini embeddings if used
if os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
# Similarly for Anthropic if it were used for embeddings (though less common for LlamaIndex default)
if os.getenv("ANTHROPIC_API_KEY"):
    os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY")


PERSIST_DIR = "./rag_index"
METADATA_DIR = "./metadata"

def main():
    if not os.path.exists(METADATA_DIR):
        print(f"Error: Metadata directory '{METADATA_DIR}' not found.")
        return

    print(f"Loading documents from '{METADATA_DIR}'...")
    # LlamaIndex's SimpleDirectoryReader will pick up .pdf files by default.
    # It uses pypdf or pymupdf, which we've included in requirements.txt.
    reader = SimpleDirectoryReader(METADATA_DIR)
    documents = reader.load_data()

    if not documents:
        print(f"No documents found in '{METADATA_DIR}'.")
        return

    print(f"Loaded {len(documents)} document(s).")
    print("Building RAG index...")
    index = VectorStoreIndex.from_documents(documents)
    
    print(f"Persisting index to '{PERSIST_DIR}'...")
    if not os.path.exists(PERSIST_DIR):
        os.makedirs(PERSIST_DIR)
    index.storage_context.persist(persist_dir=PERSIST_DIR)
    print("RAG index built and persisted successfully.")

if __name__ == "__main__":
    main() 