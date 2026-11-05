"""LangChain 版 RAG 完整示例 —— 与 LlamaIndex 版（code-rag-knowledge-base）逐一对照。

用法:
    python rag_langchain.py build --docs <文档目录> --index <索引目录>   # 建索引
    python rag_langchain.py query  --index <索引目录>                    # 交互问答

对照表（左 LangChain，右 LlamaIndex）:
    DirectoryLoader / TextLoader   -> SimpleDirectoryReader
    RecursiveCharacterTextSplitter -> LlamaIndex 内置分块
    HuggingFaceEmbeddings(bge-m3)  -> HuggingFaceEmbedding("BAAI/bge-m3")
    FAISS                          -> VectorStoreIndex + persist()
    retriever                      -> as_retriever() / query_engine

首次运行先安装依赖:
    uv add langchain langchain-openai langchain-community \
          langchain-huggingface langchain-text-splitters python-dotenv
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from dotenv import load_dotenv

# ---- LangChain 版对应 ingest.py 的导入 ----
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_community.vectorstores import FAISS
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv()


def build_index(docs_dir: Path, index_dir: Path) -> None:
    """对应 LlamaIndex 版 ingest.py 的 main()。"""
    if not docs_dir.exists() or not any(docs_dir.iterdir()):
        print(f"⚠️  {docs_dir} 为空，请先放入文档。")
        return

    # 1. 加载（LlamaIndex: SimpleDirectoryReader）
    loader = DirectoryLoader(
        str(docs_dir),
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    docs = loader.load()
    print(f"📄 已读取 {len(docs)} 个文档块")

    # 2. 切分（LlamaIndex: 内置分块器）
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )
    chunks = splitter.split_documents(docs)
    print(f"✂️  切分为 {len(chunks)} 个块")

    # 3. 向量化 + 入库（LlamaIndex: VectorStoreIndex.from_documents + persist）
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")
    vectorstore = FAISS.from_documents(chunks, embeddings)
    vectorstore.save_local(str(index_dir))
    print(f"✅ 索引已保存到 {index_dir}")


def query_index(index_dir: Path) -> None:
    """对应 LlamaIndex 版 query.py 的 main()。"""
    api_key = os.getenv("DEEPSEEK_API_KEY", "").strip()
    if not api_key or api_key.startswith("sk-xxx"):
        print("❌ 请在 .env 中填写 DEEPSEEK_API_KEY。")
        return

    if not index_dir.exists():
        print(f"⚠️  未找到索引，请先运行: python rag_langchain.py build ...")
        return

    # LLM（LlamaIndex: Settings.llm = DeepSeek(...)）
    llm = ChatOpenAI(
        model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        api_key=api_key,
        base_url=os.getenv("DEEPSEEK_BASE_URL"),
    )
    # Embedding 必须与 build 时一致
    embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")

    vectorstore = FAISS.load_local(
        str(index_dir), embeddings,
        allow_dangerous_deserialization=True,   # 本地索引，信任来源才开启
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})

    # 组装 RAG 链（LlamaIndex: index.as_query_engine(similarity_top_k=5)）
    prompt = ChatPromptTemplate.from_messages([
        ("system", "只根据提供的资料回答，资料没有的就说不知道。资料：\n{context}"),
        ("human", "{question}"),
    ])

    def format_docs(docs) -> str:
        return "\n\n".join(doc.page_content for doc in docs)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    print("💬 知识库问答已就绪。输入问题回车提问，输入 exit 退出。")
    while True:
        q = input("\nQ: ").strip()
        if q.lower() in ("exit", "quit", "退出"):
            break
        if not q:
            continue
        try:
            resp = rag_chain.invoke(q)
            print(f"\nA: {resp}")
        except Exception as exc:  # noqa: BLE001
            print(f"❌ 查询出错: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(description="LangChain 版 RAG 示例")
    sub = parser.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="构建索引")
    b.add_argument("--docs", type=Path, default=Path("docs"))
    b.add_argument("--index", type=Path, default=Path("storage/faiss"))

    q = sub.add_parser("query", help="问答")
    q.add_argument("--index", type=Path, default=Path("storage/faiss"))

    args = parser.parse_args()
    if args.cmd == "build":
        build_index(args.docs, args.index)
    elif args.cmd == "query":
        query_index(args.index)


if __name__ == "__main__":
    main()
