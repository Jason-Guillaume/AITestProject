import os
import re
import socket
import ipaddress
import urllib.request
from urllib.parse import urlparse
from pathlib import Path

from django.conf import settings

try:
    from celery import shared_task
except Exception:  # pragma: no cover
    # Celery 未安装时的兼容装饰器：保证模块可导入，不阻塞 Django 启动。
    def shared_task(*_args, **_kwargs):  # type: ignore
        def _decorator(func):
            return func

        return _decorator

from assistant.services.rag_service import process_and_embed_document
from assistant.knowledge_rag import KnowledgeIndexer
from assistant.models import KnowledgeDocument
from assistant.error_parser import simplify_vector_error


def _is_public_hostname(hostname: str) -> bool:
    """
    基础 SSRF 防护：仅允许解析到公网地址。
    """
    host = (hostname or "").strip().lower()
    if not host:
        return False
    if host in {"localhost", "127.0.0.1", "::1"}:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except Exception:
        return False
    if not infos:
        return False
    for info in infos:
        ip_str = info[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip_str)
        except ValueError:
            return False
        if (
            ip_obj.is_private
            or ip_obj.is_loopback
            or ip_obj.is_link_local
            or ip_obj.is_multicast
            or ip_obj.is_reserved
            or ip_obj.is_unspecified
        ):
            return False
    return True


def _strip_html_tags(raw_html: str) -> str:
    text = (raw_html or "").strip()
    if not text:
        return ""
    # 优先使用 bs4 提升正文抽取质量；缺失时退化为正则去标签。
    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.extract()
        text = soup.get_text(separator="\n")
    except Exception:
        text = re.sub(r"<script[\s\S]*?</script>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<style[\s\S]*?</style>", "", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _load_documents_from_url(doc: KnowledgeDocument):
    source_url = (doc.source_url or "").strip()
    if not source_url:
        raise ValueError("URL 文档缺少 source_url，无法抓取内容")
    parsed = urlparse(source_url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("URL 仅支持 http 或 https 协议")
    if not _is_public_hostname(parsed.hostname or ""):
        raise ValueError("URL 主机不可访问或疑似内网地址，已拒绝抓取")

    timeout = float(getattr(settings, "KNOWLEDGE_URL_FETCH_TIMEOUT_SECONDS", 15.0))
    max_bytes = int(getattr(settings, "KNOWLEDGE_URL_MAX_BYTES", 2 * 1024 * 1024))
    req = urllib.request.Request(
        source_url,
        method="GET",
        headers={
            "User-Agent": "AITestProduct-KnowledgeBot/1.0",
            "Accept": "text/html,application/json,text/plain,*/*;q=0.8",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw_bytes = resp.read(max_bytes + 1)
        if len(raw_bytes) > max_bytes:
            raise ValueError(f"URL 内容过大，当前最大支持 {max_bytes // 1024}KB")
        content_type = (resp.headers.get("Content-Type") or "").lower()
        charset = "utf-8"
        if "charset=" in content_type:
            charset = (content_type.split("charset=")[-1] or "utf-8").split(";")[0].strip() or "utf-8"
        raw_text = raw_bytes.decode(charset, errors="ignore").strip()
        if not raw_text:
            raise ValueError("URL 返回内容为空，无法向量化")
        if "html" in content_type or raw_text.lstrip().startswith("<"):
            text = _strip_html_tags(raw_text)
        else:
            text = raw_text
        if not text.strip():
            raise ValueError("URL 正文提取为空，无法向量化")

    try:
        from langchain_core.documents import Document
    except Exception:  # pragma: no cover
        from langchain.schema import Document  # type: ignore
    return [
        Document(
            page_content=text,
            metadata={
                "source": source_url,
                "document_type": KnowledgeDocument.DOC_TYPE_URL,
            },
        )
    ]


def _resolve_chroma_persist_dir() -> str:
    """
    统一 ChromaDB 持久化目录：
    - 优先读取 settings.KNOWLEDGE_CHROMA_PERSIST_DIR
    - 未配置时回退到 <BASE_DIR>/data/chroma
    """
    custom_dir = getattr(settings, "KNOWLEDGE_CHROMA_PERSIST_DIR", "")
    if custom_dir:
        persist_path = Path(custom_dir)
    else:
        persist_path = Path(getattr(settings, "BASE_DIR", ".")) / "data" / "chroma"
    persist_path.mkdir(parents=True, exist_ok=True)
    return str(persist_path)


def _build_loader_for_document(doc: KnowledgeDocument):
    """
    根据文档类型构建 LangChain Loader。
    本阶段按需求仅支持：
    - PDF
    - Markdown
    """
    if not doc.file_path:
        raise ValueError("文档未绑定上传文件，无法解析")
    file_path = str(doc.file_path.path)
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"上传文件不存在: {file_path}")

    suffix = Path(file_path).suffix.lower()
    if suffix not in {".pdf", ".md"}:
        raise ValueError("当前仅支持 PDF/MD 文档处理")

    try:
        from langchain_community.document_loaders import UnstructuredFileLoader
    except ImportError:  # pragma: no cover
        from langchain.document_loaders import UnstructuredFileLoader  # type: ignore

    # 使用 UnstructuredFileLoader 统一处理 PDF 与 Markdown，便于后续扩展。
    return UnstructuredFileLoader(file_path)


def _build_embeddings():
    """
    构建 embedding 模型：
    - provider=openai（默认）=> OpenAIEmbeddings
    - provider=ollama => OllamaEmbeddings
    """
    provider = (
        getattr(settings, "KNOWLEDGE_EMBEDDING_PROVIDER", "")
        or os.environ.get("KNOWLEDGE_EMBEDDING_PROVIDER", "openai")
    ).strip().lower()

    def _build_ollama_embeddings():
        model_name = (
            getattr(settings, "KNOWLEDGE_OLLAMA_EMBED_MODEL", "")
            or os.environ.get("KNOWLEDGE_OLLAMA_EMBED_MODEL", "nomic-embed-text")
        ).strip()
        base_url = (
            getattr(settings, "KNOWLEDGE_OLLAMA_BASE_URL", "")
            or os.environ.get("KNOWLEDGE_OLLAMA_BASE_URL", "http://localhost:11434")
        ).strip()
        try:
            from langchain_ollama import OllamaEmbeddings
        except ImportError:  # pragma: no cover
            from langchain_community.embeddings import OllamaEmbeddings  # type: ignore
        return OllamaEmbeddings(model=model_name, base_url=base_url)

    if provider == "ollama":
        return _build_ollama_embeddings()

    openai_model = (
        getattr(settings, "KNOWLEDGE_OPENAI_EMBED_MODEL", "")
        or os.environ.get("KNOWLEDGE_OPENAI_EMBED_MODEL", "text-embedding-3-small")
    ).strip()
    kwargs = {"model": openai_model}
    openai_api_key = (
        getattr(settings, "OPENAI_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
    ).strip()
    openai_base_url = (
        getattr(settings, "OPENAI_BASE_URL", "") or os.environ.get("OPENAI_BASE_URL", "")
    ).strip()
    if openai_api_key:
        kwargs["api_key"] = openai_api_key
    if openai_base_url:
        kwargs["base_url"] = openai_base_url

    # 防呆策略：
    # - provider=openai 但未配置 OPENAI_API_KEY 时，自动降级尝试 Ollama；
    # - 若 Ollama 不可用，再抛出明确中文错误提示，指导用户配置。
    if not openai_api_key:
        try:
            return _build_ollama_embeddings()
        except Exception:
            raise RuntimeError(
                "未检测到 OPENAI_API_KEY，且无法使用 Ollama Embeddings。"
                "请配置 OPENAI_API_KEY，或设置 KNOWLEDGE_EMBEDDING_PROVIDER=ollama 并启动 Ollama 服务。"
            )
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(**kwargs)


def _build_semantic_payload(chunks):
    chunk_rows = []
    for idx, chunk in enumerate(chunks[:12]):
        text = (getattr(chunk, "page_content", "") or "").strip()
        if not text:
            continue
        chunk_rows.append({"id": f"chunk-{idx}", "text": text[:420]})
    summary = "；".join([x["text"][:48] for x in chunk_rows[:4]])
    return summary[:500], chunk_rows


def _build_semantic_payload_from_text(raw_text: str):
    text = (raw_text or "").strip()
    if not text:
        return "", []
    rows = []
    for idx, part in enumerate(text.splitlines()):
        chunk = (part or "").strip()
        if not chunk:
            continue
        rows.append({"id": f"line-{idx}", "text": chunk[:420]})
        if len(rows) >= 12:
            break
    if not rows:
        rows = [{"id": "line-0", "text": text[:420]}]
    summary = "；".join([x["text"][:48] for x in rows[:4]])
    return summary[:500], rows


@shared_task(name="assistant.process_document_rag")
def process_document_rag(document_id: int) -> None:
    """
    知识文档 RAG 异步处理任务。
    处理流程：
    1) 读取文档（UnstructuredFileLoader，支持 PDF/MD）
    2) 文本切片（chunk_size=800, chunk_overlap=100）
    3) 注入元数据（module_id/doc_id 等）
    4) 写入 Chroma 本地持久化库
    5) 回写任务状态（处理中 -> 已完成/失败）
    """
    doc = KnowledgeDocument.objects.filter(pk=int(document_id), is_deleted=False).first()
    if doc is None:
        raise ValueError(f"KnowledgeDocument 不存在: id={document_id}")

    try:
        # 任务开始：先将状态切到“处理中”，并清空历史错误信息。
        doc.status = KnowledgeDocument.STATUS_PROCESSING
        doc.error_message = ""
        doc.save(update_fields=["status", "error_message", "update_time"])

        if doc.document_type == KnowledgeDocument.DOC_TYPE_URL:
            raw_documents = _load_documents_from_url(doc)
        else:
            loader = _build_loader_for_document(doc)
            raw_documents = loader.load()
        if not raw_documents:
            raise ValueError("文档内容为空，无法切片向量化")

        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
        except ImportError:  # langchain>=1.0
            from langchain_text_splitters import RecursiveCharacterTextSplitter
        try:
            from langchain_chroma import Chroma
        except ImportError:  # pragma: no cover
            from langchain_community.vectorstores import Chroma  # type: ignore

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=800,
            chunk_overlap=100,
        )
        chunks = splitter.split_documents(raw_documents)
        if not chunks:
            raise ValueError("切片后没有有效文本块")

        # 为每个切片注入检索关键元数据，便于后续按模块/文档精准检索。
        for idx, chunk in enumerate(chunks):
            base_meta = chunk.metadata if isinstance(chunk.metadata, dict) else {}
            chunk.metadata = {
                **base_meta,
                "doc_id": int(doc.id),
                "module_id": int(doc.module_id) if doc.module_id else None,
                "chunk_index": idx,
                "document_type": doc.document_type,
                "file_name": doc.file_name or "",
                "source_url": doc.source_url or "",
            }

        persist_directory = _resolve_chroma_persist_dir()
        collection_name = getattr(
            settings, "KNOWLEDGE_CHROMA_COLLECTION", "knowledge_documents"
        )
        embeddings = _build_embeddings()

        # 为了避免同一文档重复入库，先按 doc_id 删除旧向量，再执行 upsert。
        vector_store = Chroma(
            collection_name=collection_name,
            embedding_function=embeddings,
            persist_directory=persist_directory,
        )
        vector_store.delete(where={"doc_id": int(doc.id)})
        vector_store.add_documents(chunks)

        # 记录向量库标识，便于后续追踪：collection:doc_id。
        semantic_summary, semantic_chunks = _build_semantic_payload(chunks)
        doc.vector_db_id = f"{collection_name}:{int(doc.id)}"
        doc.semantic_summary = semantic_summary
        doc.semantic_chunks = semantic_chunks
        doc.status = KnowledgeDocument.STATUS_COMPLETED
        doc.error_message = ""
        doc.save(
            update_fields=[
                "vector_db_id",
                "semantic_summary",
                "semantic_chunks",
                "status",
                "error_message",
                "update_time",
            ]
        )
    except Exception as exc:
        # 出错时写入失败原因并回滚状态到“失败”，便于前端可见化定位问题。
        doc.status = KnowledgeDocument.STATUS_FAILED
        doc.error_message = simplify_vector_error(exc)
        doc.save(update_fields=["status", "error_message", "update_time"])
        raise


@shared_task(name="assistant.process_knowledge_document")
def process_knowledge_document_task(doc_id: int) -> None:
    process_and_embed_document(int(doc_id))


@shared_task(name="assistant.process_knowledge_article")
def process_knowledge_article_task(article_id: int, doc_id: int | None = None) -> None:
    doc = None
    if doc_id is not None:
        doc = KnowledgeDocument.objects.filter(pk=doc_id, is_deleted=False).first()
        if doc is not None:
            doc.status = KnowledgeDocument.STATUS_PROCESSING
            doc.error_message = ""
            doc.save(update_fields=["status", "error_message", "update_time"])
    try:
        ok = KnowledgeIndexer.index_article(int(article_id))
        if not ok:
            raise RuntimeError("知识文章向量化失败（索引器返回 False）")
        if doc is not None:
            summary, chunks = _build_semantic_payload_from_text(
                (getattr(doc.article, "markdown_content", "") or "")
            )
            doc.status = KnowledgeDocument.STATUS_COMPLETED
            doc.semantic_summary = summary
            doc.semantic_chunks = chunks
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
        if doc is not None:
            doc.status = KnowledgeDocument.STATUS_FAILED
            doc.error_message = simplify_vector_error(exc)
            doc.save(update_fields=["status", "error_message", "update_time"])
        raise
