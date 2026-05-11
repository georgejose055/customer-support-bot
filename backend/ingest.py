from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
import os

def build_vectorstore(docs_path="docs/"):
    docs = []
    for file in os.listdir(docs_path):
        path = os.path.join(docs_path, file)
        if file.endswith(".pdf"):
            docs += PyPDFLoader(path).load()
        elif file.endswith(".txt"):
            docs += TextLoader(path, encoding="utf-8").load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(docs)

    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local("vectorstore")
    print(f"✅ Vectorstore built with {len(chunks)} chunks")

if __name__ == "__main__":
    build_vectorstore()