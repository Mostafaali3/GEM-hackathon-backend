import os
import shutil
from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

# Configuration
DATA_PATH = "./data"
CHROMA_PATH = "./chroma_db"

def main():
    # 1. Check if data folder exists
    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH)
        print(f" Created '{DATA_PATH}' folder. Please add PDF files there and run this script again.")
        return

    # 2. Clear old database (optional, ensures fresh start)
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)

    # 3. Load Documents
    print("Loading PDF documents...")
    loader = DirectoryLoader(DATA_PATH, glob="*.pdf")
    documents = loader.load()
    
    if not documents:
        print("No documents found in ./data")
        return

    # 4. Split Text
    print("Splitting text...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=500,
        length_function=len,
        add_start_index=True,
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Created {len(chunks)} text chunks.")

    # 5. Create Vector Store (Persists automatically)
    print("Creating vector database...")
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-small-en-v1.5")
    
    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_PATH
    )
    print(f"Database created at {CHROMA_PATH}")

if __name__ == "__main__":
    main()