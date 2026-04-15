from __future__ import annotations

import os
from pathlib import Path

from django.conf import settings

from assistant.models import KnowledgeDocument
from assistant.error_parser import simplify_vector_error


def _resolve_document_path(doc: KnowledgeDocument) -> str:
    if not doc.file_path:
        raise ValueError("文档未绑定文件")
    return str(doc.file_path.path)


def _build_loader(file_path: str):
    Docx2txtLoader, PyPDFLoader, TextLoader, UnstructuredFileLoader = (
        _import_document_loaders()
    )
    suffix = Path(file_path).suffix.lower()
    if suffix == ".pdf":
        return PyPDFLoader(file_path)
    if suffix in {".docx", ".doc"}:
        return Docx2txtLoader(file_path)
    if suffix in {".txt", ".md", ".csv", ".json"}:
        return TextLoader(file_path, encoding="utf-8")
    return UnstructuredFileLoader(file_path)


def _import_document_loaders():
    try:
        from langchain_community.document_loaders import (
            Docx2txtLoader,
            PyPDFLoader,
            TextLoader,
            UnstructuredFileLoader,
        )
    except ImportError:
        from langchain.document_loaders import (  # type: ignore
            Docx2txtLoader,
            PyPDFLoader,
            TextLoader,
            UnstructuredFileLoader,
        )
    return Docx2txtLoader, PyPDFLoader, TextLoader, UnstructuredFileLoader


def _import_vector_components():
    try:
        from langchain_chroma import Chroma
    except ImportError:
        try:
            from langchain_community.vectorstores import Chroma
        except ImportError:
            from langchain.vectorstores import Chroma  # type: ignore
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_openai import OpenAIEmbeddings

    return Chroma, RecursiveCharacterTextSplitter, OpenAIEmbeddings


def _build_semantic_payload(chunks):
    rows = []
    for idx, chunk in enumerate((chunks or [])[:12]):
        text = (getattr(chunk, "page_content", "") or "").strip()
        if not text:
            continue
        rows.append({"id": f"chunk-{idx}", "text": text[:420]})
    summary = "；".join([x["text"][:48] for x in rows[:4]])
    return summary[:500], rows


def process_and_embed_document(doc_id: int) -> None:
    """
    解析并向量化 KnowledgeDocument 对应文件，然后写入本地 Chroma。
    """
    doc = KnowledgeDocument.objects.filter(pk=doc_id, is_deleted=False).first()
    if doc is None:
        raise ValueError(f"KnowledgeDocument 不存在: id={doc_id}")

    doc.status = KnowledgeDocument.STATUS_PROCESSING
    doc.error_message = ""
    doc.save(update_fields=["status", "error_message", "update_time"])

    try:
        Chroma, RecursiveCharacterTextSplitter, OpenAIEmbeddings = (
            _import_vector_components()
        )
        file_path = _resolve_document_path(doc)
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        loader = _build_loader(file_path)
        documents = loader.load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
        )
        chunks = splitter.split_documents(documents)
        if not chunks:
            raise ValueError("文档解析后内容为空，无法进行向量化")

        embeddings = OpenAIEmbeddings()

        persist_directory = str(Path(settings.BASE_DIR) / "chroma_db")
        collection_name = "knowledge_documents"
        source_name = os.path.basename(file_path)

        for idx, chunk in enumerate(chunks):
            base_meta = chunk.metadata if isinstance(chunk.metadata, dict) else {}
            chunk.metadata = {
                **base_meta,
                "doc_id": int(doc.id),
                "title": doc.title or "",
                "category": doc.category or "",
                "chunk_index": idx,
                "source": source_name,
            }

        Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=persist_directory,
            collection_name=collection_name,
        )

        semantic_summary, semantic_chunks = _build_semantic_payload(chunks)
        doc.status = KnowledgeDocument.STATUS_COMPLETED
        doc.semantic_summary = semantic_summary
        doc.semantic_chunks = semantic_chunks
        doc.error_message = ""
        doc.save(
            update_fields=[
                "status",
                "semantic_summary",
                "semantic_chunks",
                "error_message",
                "update_time",
            ]
        )
    except Exception as exc:
        doc.status = KnowledgeDocument.STATUS_FAILED
        doc.error_message = simplify_vector_error(exc)
        doc.save(update_fields=["status", "error_message", "update_time"])
        raise
