import os
import argparse
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from dotenv import load_dotenv

# Load API keys from .env file, needed for embedding models
load_dotenv()
if os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GOOGLE_API_KEY")
if os.getenv("ANTHROPIC_API_KEY"):
    os.environ["ANTHROPIC_API_KEY"] = os.getenv("ANTHROPIC_API_KEY")

def main():
    parser = argparse.ArgumentParser(description="Build a RAG index from PDF documents.")
    parser.add_argument("--metadata-dir", default="./metadata", help="Directory containing PDF files for the RAG index.")
    parser.add_argument("--index-dir", default="./rag_index", help="Directory to save the generated RAG index.")
    args = parser.parse_args()

    metadata_dir = args.metadata_dir
    persist_dir = args.index_dir

    if not os.path.exists(metadata_dir):
        print(f"Error: Metadata directory '{metadata_dir}' not found.")
        exit(1)

    print(f"Loading documents from '{metadata_dir}'...")
    reader = SimpleDirectoryReader(metadata_dir)
    documents = reader.load_data()

    if not documents:
        print(f"No documents found in '{metadata_dir}'. Exiting.")
        return

    print(f"Loaded {len(documents)} document(s). Building RAG index...")
    index = VectorStoreIndex.from_documents(documents)
    
    print(f"Persisting index to '{persist_dir}'...")
    if not os.path.exists(persist_dir):
        os.makedirs(persist_dir)
    index.storage_context.persist(persist_dir=persist_dir)
    print("RAG index built and persisted successfully.")

if __name__ == "__main__":
    main() 