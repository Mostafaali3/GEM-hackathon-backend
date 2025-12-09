import os
from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma                   # New Chroma package
from langchain_huggingface import HuggingFaceEmbeddings # New HF package
from langchain_ollama import ChatOllama               # New Ollama package
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

DATA_PATH = "./data"          # Ensure this folder exists and contains PDFs
PERSIST_DIR = "./chroma_db"   # Folder for vector DB

def load_documents():
    if not os.path.exists(DATA_PATH):
        os.makedirs(DATA_PATH)
        print(f"Created {DATA_PATH}. Please put your PDFs here.")
        return []
    # Uses 'unstructured' or 'pypdf' under the hood
    loader = DirectoryLoader(DATA_PATH, glob="*.pdf") 
    documents = loader.load()
    return documents

def main():
    documents = load_documents()
    
    if not documents:
        print("No documents found. Exiting.")
        return

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=500,
        length_function=len,
        add_start_index=True,
    )
    texts = text_splitter.split_documents(documents)
    print(f"Total chunks created: {len(texts)}")

    embeddings = HuggingFaceEmbeddings(
        model_name="BAAI/bge-small-en-v1.5" 
    )

    # 6️⃣ Vector Store (Updated Class)
    # Note: In langchain_chroma, persistence is automatic if persist_directory is set.
    # We use .from_documents to load data, or just load the existing DB if it exists.
    if os.path.exists(PERSIST_DIR) and os.listdir(PERSIST_DIR):
        print("Loading existing vector store...")
        vectordb = Chroma(persist_directory=PERSIST_DIR, embedding_function=embeddings)
    else:
        print("Creating new vector store...")
        vectordb = Chroma.from_documents(
            documents=texts,
            embedding=embeddings,
            persist_directory=PERSIST_DIR
        )

    # 7️⃣ Initialize Ollama (Updated Class)
    # Ensure you have run `ollama pull llama3` (or your specific model) in terminal first
    llm = ChatOllama(
        model="deepseek-v3.1:671b-cloud",  # Changed to a standard model for testing; revert to your custom tag if needed
        temperature=0
    )

    # 8️⃣ Setup Retrieval Chain (LCEL Style)
    retriever = vectordb.as_retriever(search_kwargs={"k": 5})

    template = """
    You are a helpful assistant.
    Use ONLY the context below to answer the question.
    Do NOT copy long text verbatim. Summarize concisely.
    If the answer is not in context, reply: "Not found in document."

    Context:
    {context}

    Question:
    {question}

    Answer:
    """

    prompt = PromptTemplate.from_template(template)

    # This function formats documents into a single string
    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    # The LCEL Chain: Retriever -> Formatter -> Prompt -> LLM -> Output Parser
    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    # 9️⃣ Interactive Loop
    while True:
        user_query = input("\nAsk a question (or 'q' to quit): ")
        if user_query.lower() == 'q':
            break
            
        print("\nThinking...")
        # invoke the chain
        response = rag_chain.invoke(user_query)
        
        print("\n=== RAG Answer ===\n")
        print(response)

if __name__ == "__main__":
    main()