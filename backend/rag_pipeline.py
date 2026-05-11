from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from dotenv import load_dotenv
import os

load_dotenv()

ESCALATION_PHRASES = [
    "speak to human", "talk to agent", "human please",
    "not helpful", "connect me to agent", "real person"
]

UNCERTAINTY_SIGNALS = [
    "i'm not sure", "i don't know", "cannot find",
    "no information", "not available", "i cannot answer"
]

def load_chain():
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = FAISS.load_local(
        "vectorstore", embeddings, allow_dangerous_deserialization=True
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

    llm = ChatGroq(
        model="llama-3.1-8b-instant",
        api_key=os.getenv("GROQ_API_KEY")
    )

    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""You are a polite and helpful customer support agent.
Use only the context below to answer. If the answer is not in the context,
say exactly: "I'm not sure about that, let me connect you to a human agent."

Context: {context}
Question: {question}
Answer:"""
    )

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    return chain

def get_response(chain, user_message: str) -> str:
    result = chain.invoke({"query": user_message})
    # Extract string from dict if needed
    if isinstance(result, dict):
        return result.get("answer") or result.get("result") or str(result)
    return str(result)