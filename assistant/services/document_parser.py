from __future__ import annotations

import io
import os

try:
    import pdfplumber
except ImportError:  # pragma: no cover
    pdfplumber = None  # type: ignore

try:
    from docx import Document
except ImportError:  # pragma: no cover
    Document = None  # type: ignore


SUPPORTED_EXTENSIONS = {".txt", ".md", ".pdf", ".docx"}


def extract_text_from_uploaded_file(uploaded_file) -> str:
    """
    根据文件扩展名提取纯文本内容。
    :param uploaded_file: Django InMemoryUploadedFile / TemporaryUploadedFile
    """
    if uploaded_file is None:
        raise ValueError("未提供上传文件")
    filename = getattr(uploaded_file, "name", "") or ""
    ext = os.path.splitext(filename.lower())[1]
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError("仅支持 .txt/.md/.pdf/.docx 文件")

    raw = uploaded_file.read()
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)

    if ext in {".txt", ".md"}:
        return _decode_text(raw)
    if ext == ".pdf":
        return _extract_pdf_text(raw)
    if ext == ".docx":
        return _extract_docx_text(raw)
    return ""


def _decode_text(raw: bytes) -> str:
    for enc in ("utf-8", "utf-8-sig", "gbk", "gb18030"):
        try:
            return raw.decode(enc)
        except Exception:
            continue
    return raw.decode("utf-8", errors="ignore")


def _extract_pdf_text(raw: bytes) -> str:
    if pdfplumber is None:
        raise ValueError("未安装 pdfplumber，请先安装依赖后再解析 PDF")
    text_parts = []
    with pdfplumber.open(io.BytesIO(raw)) as pdf:
        for page in pdf.pages:
            page_text = (page.extract_text() or "").strip()
            if page_text:
                text_parts.append(page_text)
    return "\n\n".join(text_parts).strip()


def _extract_docx_text(raw: bytes) -> str:
    if Document is None:
        raise ValueError("未安装 python-docx，请先安装依赖后再解析 DOCX")
    doc = Document(io.BytesIO(raw))
    lines = [(p.text or "").strip() for p in doc.paragraphs]
    return "\n".join([x for x in lines if x]).strip()
