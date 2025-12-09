# 1️⃣ Imports
import os
from langchain_community.document_loaders import DirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import PromptTemplate
from langchain_community.chat_models import ChatOllama

# 2️⃣ Set paths
DATA_PATH = "D:\College\Extra-curriculum activities\GEM hackathon"              # folder containing your PDFs locally
PERSIST_DIR = "./chroma_store"    # folder to save vector DB

# 3️⃣ Load PDF documents
def load_documents():
    loader = DirectoryLoader(DATA_PATH, glob="*.pdf")
    documents = loader.load()
    return documents

documents = load_documents()

# 4️⃣ Split documents into chunks
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=500,
    length_function=len,
    add_start_index=True,
)

texts = text_splitter.split_documents(documents)

print(f"Total chunks: {len(texts)}")
print(f"First chunk:\n{texts[0].page_content[:500]}...")  # show first 500 chars

# 5️⃣ Create embeddings
embeddings = HuggingFaceEmbeddings(
    model_name="BAAI/bge-small-en-v1.5"
)

# 6️⃣ Create or load Chroma vector DB
vectordb = Chroma.from_documents(
    documents=texts,
    embedding=embeddings,
    persist_directory=PERSIST_DIR
)

vectordb.persist()

# 7️⃣ Initialize Ollama LLM
llm = ChatOllama(
    model="deepeek-v3.1:671b-cloud",   # or "llama3", "mixtral", etc.
    temperature=0
)

# 8️⃣ Ask user for a question
user_query = input("Ask a question: ")

# 9️⃣ Retrieve top chunks from vector DB
retrieved_docs = vectordb.similarity_search(user_query, k=5)

# 10️⃣ Combine context
context = "\n\n".join([doc.page_content for doc in retrieved_docs])

# 11️⃣ Prepare RAG prompt
template = """
You are a helpful assistant.
Use ONLY the context below to answer the question.
Do NOT copy long text verbatim. Summarize concisely.
If the answer is not in context, reply: "Not found in document."
Temperature = 0.

Context:
{context}

Question:
{question}

Answer:
"""

prompt = PromptTemplate.from_template(template)
final_prompt = prompt.format(context=context, question=user_query)

# 12️⃣ Call Ollama LLM
response = llm.invoke(final_prompt, temperature=0)

# 13️⃣ Print answer
print("\n=== RAG Answer ===\n")
print(response)
