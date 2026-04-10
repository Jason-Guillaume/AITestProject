import json
import logging
import importlib.util
import re
from datetime import timedelta
from pathlib import Path
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request

from django.conf import settings
from django.http import JsonResponse, StreamingHttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from common.views import BaseModelViewSet

from rest_framework import exceptions as drf_exceptions
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

try:
    from openai import (
        APIConnectionError,
        APIError,
        APITimeoutError,
        AuthenticationError,
        OpenAI,
    )

    OPENAI_SDK_AVAILABLE = True
    _OPENAI_IMPORT_ERR = ""
except ImportError as _e:  # pragma: no cover
    OPENAI_SDK_AVAILABLE = False
    _OPENAI_IMPORT_ERR = str(_e)
    APIConnectionError = APIError = APITimeoutError = AuthenticationError = Exception  # type: ignore
    OpenAI = None  # type: ignore

from assistant.ai_generate_strategies import (
    apply_test_type_domain_strategy,
    dispatch_ai_generation,
    validate_spec,
)
from assistant.services.ai_engine import build_engine_addon
from assistant.services.case_batch_generation import (
    build_batch_generation_prompt,
    normalize_batch_case_item,
    parse_batch_json_array,
)
from assistant.services.semantic_dedup import semantic_deduplicate_cases
from assistant.api_case_generation import (
    enrich_normalized_case_with_api_fields,
    renumber_api_business_ids,
)
from assistant.generated_case_dedup import deduplicate_generated_cases
from assistant.rag_pipeline import build_rag_system_prompt, is_all_covered_output
from assistant.knowledge_rag import KnowledgeSearcher
from assistant.models import KnowledgeArticle, KnowledgeDocument
from assistant.serialize import KnowledgeArticleSerializer, KnowledgeDocumentSerializer
from assistant.error_parser import simplify_vector_error
from assistant.services.document_parser import (
    SUPPORTED_EXTENSIONS,
    extract_text_from_uploaded_file,
)
from testcase.models import TestModule

logger = logging.getLogger(__name__)


def _sanitize_doc_error_fields(payload):
    if isinstance(payload, dict):
        msg = payload.get("error_message")
        if isinstance(msg, str) and msg.strip():
            payload["error_message"] = simplify_vector_error(msg)
        return payload
    if isinstance(payload, list):
        return [_sanitize_doc_error_fields(x) for x in payload]
    return payload


def _build_fallback_semantic_payload(doc: KnowledgeDocument):
    text = ""
    try:
        if doc.source_type == KnowledgeDocument.SOURCE_ARTICLE and doc.article_id:
            article_text = (getattr(doc.article, "markdown_content", "") or "").strip()
            if article_text:
                text = article_text
        if doc.file_path and getattr(doc.file_path, "path", None):
            file_path = Path(doc.file_path.path)
            if file_path.exists():
                suffix = file_path.suffix.lower()
                if suffix in {".md", ".txt", ".json", ".csv"}:
                    text = file_path.read_text(encoding="utf-8", errors="ignore")
                elif suffix == ".pdf":
                    try:
                        import pdfplumber

                        parts = []
                        with pdfplumber.open(str(file_path)) as pdf:
                            for page in pdf.pages[:10]:
                                parts.append((page.extract_text() or "").strip())
                        text = "\n".join([x for x in parts if x])
                    except Exception:
                        text = ""
        if not text and doc.source_url:
            text = f"URL 文档：{doc.source_url}"
    except Exception:
        text = ""
    content = (text or "").strip()
    if not content:
        return "", []
    rows = []
    for i, part in enumerate(re.split(r"\n{2,}|。", content)):
        chunk = (part or "").strip()
        if not chunk:
            continue
        rows.append({"id": f"fallback-{i}", "text": chunk[:420]})
        if len(rows) >= 12:
            break
    summary = "；".join([x["text"][:48] for x in rows[:4]])[:500]
    return summary, rows


def _infer_doc_form_fallback(text: str, filename: str, module_options: list[dict]):
    body = (text or "").strip()
    lower = body.lower()
    purpose = "requirement"
    if re.search(r"模板|计划|报告|复盘|周报|日报|里程碑", body):
        purpose = "template"
    elif re.search(r"规范|标准|准则|流程|制度|sop|最佳实践", lower):
        purpose = "standard"

    title = ""
    for line in body.splitlines():
        ln = (line or "").strip()
        if 4 <= len(ln) <= 40:
            title = ln
            break
    if not title:
        title = (filename or "").strip()

    module_id = None
    if body and module_options:
        best_score = 0
        for row in module_options:
            name = (row.get("name") or "").strip()
            if len(name) < 2:
                continue
            if name in body and len(name) > best_score:
                best_score = len(name)
                module_id = row.get("id")

    dict_words = [
        "登录", "注册", "鉴权", "权限", "接口", "API", "状态码", "并发", "性能", "安全",
        "SQL注入", "越权", "支付", "订单", "用户", "搜索", "消息", "文件上传", "边界", "异常",
    ]
    tags = []
    for word in dict_words:
        if word.lower() in lower:
            tags.append(word)
        if len(tags) >= 6:
            break
    return {
        "title": title[:255],
        "purpose": purpose,
        "module_id": module_id,
        "tags": tags,
        "source": "fallback",
    }


def _infer_doc_form_with_llm(text: str, filename: str, module_options: list[dict]):
    fallback = _infer_doc_form_fallback(text=text, filename=filename, module_options=module_options)
    text = (text or "").strip()
    if not text:
        return fallback
    try:
        api_key, api_base_url, model_used = _get_active_ai_model_credentials()
    except Exception:
        return fallback
    if not api_key or not api_base_url or not model_used or not OPENAI_SDK_AVAILABLE:
        return fallback

    module_names = [str(x.get("name") or "").strip() for x in module_options if str(x.get("name") or "").strip()]
    module_names_text = "、".join(module_names[:120]) if module_names else "（无模块可选）"
    snippet = text[:12000]
    system_prompt = (
        "你是文档入库助手。请根据文档内容提取表单预填信息。"
        "只输出一个 JSON 对象，不要输出任何额外说明。"
        "JSON 结构："
        '{"title":"", "purpose":"requirement|standard|template", "module_name":"", "tags":[""], "reason":""}'
    )
    user_prompt = (
        f"文件名：{filename or '未提供'}\n"
        f"可选模块：{module_names_text}\n\n"
        f"文档内容：\n{snippet}"
    )
    try:
        client = OpenAI(api_key=api_key, base_url=api_base_url, timeout=25.0)
        resp = client.chat.completions.create(
            model=model_used,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=600,
        )
        raw = (resp.choices[0].message.content or "").strip()
        md = re.search(r"\{[\s\S]*\}", raw)
        payload = (md.group(0) if md else raw).strip()
        data = json.loads(payload)
        if not isinstance(data, dict):
            return fallback
        purpose = str(data.get("purpose") or fallback["purpose"]).strip()
        if purpose not in {"requirement", "standard", "template"}:
            purpose = fallback["purpose"]
        title = str(data.get("title") or fallback["title"]).strip()[:255]
        tag_rows = data.get("tags")
        tags = []
        if isinstance(tag_rows, list):
            tags = [str(x).strip() for x in tag_rows if str(x).strip()][:8]
        module_name = str(data.get("module_name") or "").strip()
        module_id = fallback.get("module_id")
        if module_name:
            for row in module_options:
                name = str(row.get("name") or "").strip()
                if not name:
                    continue
                if module_name == name or module_name in name or name in module_name:
                    module_id = row.get("id")
                    break
        return {
            "title": title or fallback["title"],
            "purpose": purpose,
            "module_id": module_id,
            "tags": tags or fallback["tags"],
            "source": "llm",
        }
    except Exception:
        return fallback


def _mark_stuck_processing_docs_failed() -> int:
    """
    将长时间处于 processing 的任务标记为 failed，避免页面长期卡住。
    """
    timeout_minutes = int(getattr(settings, "KNOWLEDGE_PROCESSING_TIMEOUT_MINUTES", 10))
    timeout_minutes = max(1, timeout_minutes)
    deadline = timezone.now() - timedelta(minutes=timeout_minutes)
    qs = KnowledgeDocument.objects.filter(
        is_deleted=False,
        status=KnowledgeDocument.STATUS_PROCESSING,
        update_time__lt=deadline,
    )[:200]
    changed = 0
    for doc in qs:
        doc.status = KnowledgeDocument.STATUS_FAILED
        if not (doc.error_message or "").strip():
            doc.error_message = f"处理超时（超过 {timeout_minutes} 分钟未完成），请重试"
        doc.save(update_fields=["status", "error_message", "update_time"])
        changed += 1
    return changed


class KnowledgeArticleViewSet(BaseModelViewSet):
    queryset = KnowledgeArticle.objects.all()
    serializer_class = KnowledgeArticleSerializer
    parser_classes = (JSONParser, MultiPartParser, FormParser)

    def get_queryset(self):
        qs = super().get_queryset()
        category = (self.request.query_params.get("category") or "").strip()
        tag = (self.request.query_params.get("tag") or "").strip()
        if category:
            qs = qs.filter(category=category)
        if tag:
            qs = qs.filter(tags__contains=[tag])
        return qs.order_by("-create_time")

    def create(self, request, *args, **kwargs):
        payload = request.data.copy()
        text_source = (payload.get("text_source") or "manual").strip()
        uploaded_file = request.FILES.get("source_file")
        if "source_file" in payload:
            payload.pop("source_file")
        if "text_source" in payload:
            payload.pop("text_source")
        if uploaded_file is not None:
            max_size = int(getattr(settings, "KNOWLEDGE_UPLOAD_MAX_SIZE", 10 * 1024 * 1024))
            if int(getattr(uploaded_file, "size", 0) or 0) > max_size:
                return Response({"msg": f"上传文件过大，最大支持 {max_size // 1024 // 1024}MB"}, status=400)
            try:
                payload["markdown_content"] = extract_text_from_uploaded_file(uploaded_file)
            except ValueError as exc:
                return Response({"msg": str(exc)}, status=400)
            except Exception:
                logger.exception("解析知识库上传文件失败: filename=%s", getattr(uploaded_file, "name", ""))
                return Response({"msg": "文件解析失败，请检查文件格式或内容后重试"}, status=400)
        elif text_source == "upload" and not (payload.get("markdown_content") or "").strip():
            return Response({"msg": "请选择文件或填写内容"}, status=400)

        tags_val = payload.get("tags")
        if isinstance(tags_val, str):
            tags_val = tags_val.strip()
            if tags_val.startswith("["):
                try:
                    payload["tags"] = json.loads(tags_val)
                except Exception:
                    payload["tags"] = [x.strip() for x in tags_val.split(",") if x.strip()]
            else:
                payload["tags"] = [x.strip() for x in tags_val.split(",") if x.strip()]

        serializer = self.get_serializer(data=payload)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=201, headers=headers)


class KnowledgeExtractTextAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            return Response({"success": False, "message": "请先选择文件"}, status=400)
        max_size = int(getattr(settings, "KNOWLEDGE_UPLOAD_MAX_SIZE", 10 * 1024 * 1024))
        if int(getattr(uploaded_file, "size", 0) or 0) > max_size:
            return Response(
                {"success": False, "message": f"上传文件过大，最大支持 {max_size // 1024 // 1024}MB"},
                status=400,
            )
        ext = (uploaded_file.name or "").lower()
        if not any(ext.endswith(x) for x in SUPPORTED_EXTENSIONS):
            return Response(
                {"success": False, "message": "仅支持 .txt/.md/.pdf/.docx 文件"},
                status=400,
            )
        try:
            text = extract_text_from_uploaded_file(uploaded_file)
        except ValueError as exc:
            return Response({"success": False, "message": str(exc)}, status=400)
        except Exception:
            logger.exception("知识库文件预解析失败: filename=%s", getattr(uploaded_file, "name", ""))
            return Response({"success": False, "message": "文件解析失败"}, status=400)
        return Response(
            {
                "success": True,
                "text": text,
                "filename": uploaded_file.name,
            }
        )


class KnowledgeAutoFillFromFileAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        uploaded_file = request.FILES.get("file")
        text = (request.data.get("text") or "").strip()
        filename = (request.data.get("filename") or "").strip()

        if uploaded_file is not None:
            filename = (uploaded_file.name or "").strip() or filename
            max_size = int(getattr(settings, "KNOWLEDGE_UPLOAD_MAX_SIZE", 10 * 1024 * 1024))
            if int(getattr(uploaded_file, "size", 0) or 0) > max_size:
                return Response(
                    {"success": False, "message": f"上传文件过大，最大支持 {max_size // 1024 // 1024}MB"},
                    status=400,
                )
            ext = (uploaded_file.name or "").lower()
            if not any(ext.endswith(x) for x in SUPPORTED_EXTENSIONS):
                return Response(
                    {"success": False, "message": "仅支持 .txt/.md/.pdf/.docx 文件"},
                    status=400,
                )
            try:
                text = extract_text_from_uploaded_file(uploaded_file)
            except ValueError as exc:
                return Response({"success": False, "message": str(exc)}, status=400)
            except Exception:
                logger.exception("自动填充提取文本失败: filename=%s", getattr(uploaded_file, "name", ""))
                return Response({"success": False, "message": "文件解析失败"}, status=400)

        text = (text or "").strip()
        if not text:
            return Response({"success": False, "message": "缺少可分析文本"}, status=400)

        module_rows = list(
            TestModule.objects.filter(is_deleted=False).values("id", "name")[:300]
        )
        auto = _infer_doc_form_with_llm(text=text, filename=filename, module_options=module_rows)
        return Response(
            {
                "success": True,
                "data": {
                    "title": auto.get("title") or "",
                    "purpose": auto.get("purpose") or "requirement",
                    "module_id": auto.get("module_id"),
                    "tags": auto.get("tags") if isinstance(auto.get("tags"), list) else [],
                    "source": auto.get("source") or "fallback",
                    "text_preview": text[:800],
                },
            }
        )


class KnowledgeCategoryOptionsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        options = [
            {"value": value, "label": label}
            for value, label in KnowledgeArticle.CATEGORY_CHOICES
        ]
        return Response({"success": True, "options": options})


class KnowledgeSearchAPIView(APIView):
    """
    POST /api/assistant/knowledge/search/
    body: { "query_text": "...", "top_k": 5 }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        query_text = (request.data.get("query_text") or "").strip()
        if not query_text:
            return Response(
                {"success": False, "message": "query_text 不能为空", "results": []},
                status=400,
            )
        top_k = request.data.get("top_k", 5)
        try:
            top_k = int(top_k)
        except (TypeError, ValueError):
            top_k = 5
        top_k = max(1, min(top_k, 20))
        category = (request.data.get("category") or "").strip() or None
        tag = (request.data.get("tag") or "").strip() or None
        raw_min_score = request.data.get("min_score")
        min_score = None
        if raw_min_score not in (None, ""):
            try:
                min_score = float(raw_min_score)
            except (TypeError, ValueError):
                min_score = None
        results = KnowledgeSearcher.search_similar(
            query_text,
            top_k=top_k,
            category=category,
            tag=tag,
            min_score=min_score,
        )
        return Response(
            {
                "success": True,
                "query_text": query_text,
                "top_k": top_k,
                "category": category,
                "tag": tag,
                "min_score": min_score,
                "results": results,
            }
        )


class KnowledgeDocumentUploadAPIView(APIView):
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        uploaded_file = request.FILES.get("file")
        if uploaded_file is None:
            return Response({"success": False, "message": "file 不能为空"}, status=400)

        title = (request.data.get("title") or "").strip()
        if not title:
            return Response({"success": False, "message": "title 不能为空"}, status=400)

        category = (request.data.get("category") or "").strip()
        raw_tags = request.data.get("tags")
        tags = []
        if isinstance(raw_tags, str):
            raw = raw_tags.strip()
            if raw:
                if raw.startswith("["):
                    try:
                        parsed = json.loads(raw)
                        if isinstance(parsed, list):
                            tags = [str(x).strip() for x in parsed if str(x).strip()]
                    except Exception:
                        tags = [x.strip() for x in raw.split(",") if x.strip()]
                else:
                    tags = [x.strip() for x in raw.split(",") if x.strip()]
        elif isinstance(raw_tags, (list, tuple)):
            tags = [str(x).strip() for x in raw_tags if str(x).strip()]

        doc = KnowledgeDocument.objects.create(
            title=title,
            category=category,
            tags=tags,
            source_type=KnowledgeDocument.SOURCE_UPLOAD,
            article=None,
            file_path=uploaded_file,
            status=KnowledgeDocument.STATUS_PENDING,
            error_message="",
            creator=request.user,
            updater=request.user,
        )

        # 优先 Celery 异步；若当前环境未安装/未启动 Celery，则降级为后台线程。
        try:
            from assistant.tasks import process_knowledge_document_task

            process_knowledge_document_task.delay(int(doc.id))
            doc.status = KnowledgeDocument.STATUS_PROCESSING
            doc.save(update_fields=["status", "update_time"])
            enqueue_msg = "文档已上传，已加入异步处理队列"
        except Exception:
            import threading
            from assistant.services.rag_service import process_and_embed_document

            def _bg_process(document_id: int):
                try:
                    process_and_embed_document(document_id)
                except Exception:
                    logger.exception("知识库文档向量化失败: doc_id=%s", document_id)

            threading.Thread(
                target=_bg_process,
                args=(int(doc.id),),
                daemon=True,
            ).start()
            doc.status = KnowledgeDocument.STATUS_PROCESSING
            doc.save(update_fields=["status", "update_time"])
            enqueue_msg = "文档已上传，正在后台处理（线程降级模式）"
        return Response(
            {
                "success": True,
                "message": enqueue_msg,
                "data": KnowledgeDocumentSerializer(doc).data,
            },
            status=202,
        )


class KnowledgeDocumentIngestAPIView(APIView):
    """
    统一知识文档入库接口：
    - mode=upload: 处理文件上传（支持 PDF/MD）
    - mode=url: 提交网页 URL（文档类型固定为 URL）
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        # 1) 解析并校验基础参数。module_id 与 testcase.TestModule 关联，保证“模块分类”可追溯。
        mode = (request.data.get("mode") or "upload").strip().lower()
        raw_module_id = request.data.get("module_id")
        title = (request.data.get("title") or "").strip()
        source_url = (request.data.get("url") or "").strip()
        uploaded_file = request.FILES.get("file")

        module = None
        if raw_module_id not in (None, ""):
            try:
                module = TestModule.objects.filter(pk=int(raw_module_id), is_deleted=False).first()
            except (TypeError, ValueError):
                module = None
            if module is None:
                return Response({"success": False, "message": "module_id 无效"}, status=400)

        if mode not in ("upload", "url"):
            return Response({"success": False, "message": "mode 仅支持 upload 或 url"}, status=400)

        # 2) 按模式构建文档元数据，确保文档类型、文件名、来源字段一致。
        document_type = KnowledgeDocument.DOC_TYPE_MD
        file_name = ""
        file_path = None
        final_source_url = ""
        final_title = title

        if mode == "upload":
            if uploaded_file is None:
                return Response({"success": False, "message": "upload 模式下 file 不能为空"}, status=400)
            file_name = (getattr(uploaded_file, "name", "") or "").strip()
            if not file_name:
                return Response({"success": False, "message": "上传文件名不能为空"}, status=400)
            ext = file_name.lower()
            if ext.endswith(".pdf"):
                document_type = KnowledgeDocument.DOC_TYPE_PDF
            elif ext.endswith(".md"):
                document_type = KnowledgeDocument.DOC_TYPE_MD
            else:
                return Response({"success": False, "message": "仅支持 PDF 或 MD 文件"}, status=400)
            file_path = uploaded_file
            if not final_title:
                final_title = file_name
        else:
            if not source_url:
                return Response({"success": False, "message": "url 模式下 url 不能为空"}, status=400)
            if not (source_url.startswith("http://") or source_url.startswith("https://")):
                return Response({"success": False, "message": "URL 必须以 http:// 或 https:// 开头"}, status=400)
            document_type = KnowledgeDocument.DOC_TYPE_URL
            final_source_url = source_url
            file_name = source_url
            if not final_title:
                final_title = source_url

        # 3) 先落库，初始状态为“待处理”，后续由异步任务更新处理状态。
        document = KnowledgeDocument.objects.create(
            title=final_title[:255],
            file_name=file_name[:255],
            module=module,
            document_type=document_type,
            source_type=KnowledgeDocument.SOURCE_UPLOAD,
            file_path=file_path,
            source_url=final_source_url,
            status=KnowledgeDocument.STATUS_PENDING,
            creator=request.user,
            updater=request.user,
        )

        # 4) 异步触发 RAG 处理：优先 Celery；不可用时降级线程执行。
        from assistant.tasks import process_document_rag

        try:
            process_document_rag.delay(int(document.id))
            document.status = KnowledgeDocument.STATUS_PROCESSING
            document.save(update_fields=["status", "update_time"])
        except Exception:
            import threading

            def _bg_rag_task(document_id: int):
                try:
                    process_document_rag(int(document_id))
                except Exception:
                    logger.exception("知识文档 RAG 处理失败: doc_id=%s", document_id)

            threading.Thread(
                target=_bg_rag_task,
                args=(int(document.id),),
                daemon=True,
            ).start()
            document.status = KnowledgeDocument.STATUS_PROCESSING
            document.save(update_fields=["status", "update_time"])

        return Response(
            {
                "success": True,
                "message": "文档记录已创建，RAG 处理任务已提交",
                "data": KnowledgeDocumentSerializer(document).data,
            },
            status=202,
        )


class KnowledgeDocumentStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, doc_id: int):
        _mark_stuck_processing_docs_failed()
        doc = KnowledgeDocument.objects.filter(pk=doc_id, is_deleted=False).first()
        if doc is None:
            return Response({"success": False, "message": "文档不存在"}, status=404)
        is_admin = bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.is_staff
                or bool(getattr(request.user, "is_system_admin", False))
            )
        )
        if not is_admin and int(getattr(doc, "creator_id", 0) or 0) != int(request.user.id):
            return Response({"success": False, "message": "无权限访问该文档"}, status=403)
        if doc.status == KnowledgeDocument.STATUS_COMPLETED and not (
            (doc.semantic_summary or "").strip() or (doc.semantic_chunks or [])
        ):
            summary, chunks = _build_fallback_semantic_payload(doc)
            if summary or chunks:
                doc.semantic_summary = summary
                doc.semantic_chunks = chunks
                doc.save(update_fields=["semantic_summary", "semantic_chunks", "update_time"])
        return Response(
            {
                "success": True,
                "data": _sanitize_doc_error_fields(KnowledgeDocumentSerializer(doc).data),
            }
        )


class KnowledgeDocumentRetryAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, doc_id: int):
        doc = KnowledgeDocument.objects.filter(pk=doc_id, is_deleted=False).first()
        if doc is None:
            return Response({"success": False, "message": "文档不存在"}, status=404)
        is_admin = bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.is_staff
                or bool(getattr(request.user, "is_system_admin", False))
            )
        )
        if not is_admin and int(getattr(doc, "creator_id", 0) or 0) != int(request.user.id):
            return Response({"success": False, "message": "无权限重试该任务"}, status=403)
        # 允许待处理/失败/已完成状态重提任务；仅“处理中”禁止重复触发。
        if doc.status == KnowledgeDocument.STATUS_PROCESSING:
            return Response({"success": False, "message": "当前任务仍在处理中，无需重试"}, status=400)

        doc.status = KnowledgeDocument.STATUS_PENDING
        doc.error_message = ""
        doc.save(update_fields=["status", "error_message", "update_time"])

        if doc.source_type == KnowledgeDocument.SOURCE_ARTICLE and doc.article_id:
            try:
                from assistant.tasks import process_knowledge_article_task

                process_knowledge_article_task.delay(int(doc.article_id), int(doc.id))
            except Exception:
                import threading
                from assistant.tasks import process_knowledge_article_task

                threading.Thread(
                    target=process_knowledge_article_task,
                    args=(int(doc.article_id), int(doc.id)),
                    daemon=True,
                ).start()
        else:
            try:
                from assistant.tasks import process_knowledge_document_task

                process_knowledge_document_task.delay(int(doc.id))
            except Exception:
                import threading
                from assistant.services.rag_service import process_and_embed_document

                threading.Thread(
                    target=process_and_embed_document,
                    args=(int(doc.id),),
                    daemon=True,
                ).start()

        return Response(
            {
                "success": True,
                "message": "重试任务已提交",
                "data": KnowledgeDocumentSerializer(doc).data,
            },
            status=202,
        )


class KnowledgeDocumentDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, doc_id: int):
        doc = KnowledgeDocument.objects.filter(pk=doc_id, is_deleted=False).first()
        if doc is None:
            return Response({"success": False, "message": "文档不存在"}, status=404)
        is_admin = bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.is_staff
                or bool(getattr(request.user, "is_system_admin", False))
            )
        )
        if not is_admin and int(getattr(doc, "creator_id", 0) or 0) != int(request.user.id):
            return Response({"success": False, "message": "无权限删除该文档"}, status=403)

        doc.is_deleted = True
        doc.updater = request.user
        doc.save(update_fields=["is_deleted", "updater", "update_time"])
        return Response({"success": True, "message": "删除成功"})


class KnowledgeDocumentListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _mark_stuck_processing_docs_failed()
        page_size = request.query_params.get("page_size", 20)
        try:
            page_size = int(page_size)
        except (TypeError, ValueError):
            page_size = 20
        page_size = max(1, min(page_size, 100))
        qs = KnowledgeDocument.objects.filter(is_deleted=False)
        is_admin = bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.is_staff
                or bool(getattr(request.user, "is_system_admin", False))
            )
        )
        if not is_admin:
            qs = qs.filter(creator=request.user)
        rows = qs.order_by("-created_at")[:page_size]
        return Response(
            {
                "success": True,
                "results": _sanitize_doc_error_fields(KnowledgeDocumentSerializer(rows, many=True).data),
            }
        )


class KnowledgeRuntimeStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _mark_stuck_processing_docs_failed()
        celery_installed = importlib.util.find_spec("celery") is not None
        queue_mode = "celery" if celery_installed else "thread_fallback"
        base_qs = KnowledgeDocument.objects.filter(is_deleted=False)
        is_admin = bool(
            request.user
            and request.user.is_authenticated
            and (
                request.user.is_superuser
                or request.user.is_staff
                or bool(getattr(request.user, "is_system_admin", False))
            )
        )
        if not is_admin:
            base_qs = base_qs.filter(creator=request.user)
        counters = {
            "pending": base_qs.filter(status=KnowledgeDocument.STATUS_PENDING).count(),
            "processing": base_qs.filter(status=KnowledgeDocument.STATUS_PROCESSING).count(),
            "completed": base_qs.filter(status=KnowledgeDocument.STATUS_COMPLETED).count(),
            "failed": base_qs.filter(status=KnowledgeDocument.STATUS_FAILED).count(),
        }
        return Response(
            {
                "success": True,
                "queue_mode": queue_mode,
                "celery_installed": celery_installed,
                "counters": counters,
            }
        )


def _debug_log_openai_target(scene: str, model: str, base_url: str):
    """仅在 DEBUG=True 时打印最终调用目标，便于排查 404/路由问题。"""
    if not settings.DEBUG:
        return
    logger.info(
        "[AI_TARGET_DEBUG] scene=%s model=%s base_url=%s",
        scene,
        model,
        base_url,
    )


def _openai_missing_response_json(msg_prefix: str = "服务端未检测到 openai 库"):
    """提示用户在「运行 Django 的同一解释器」下安装依赖。"""
    hint = (
        f"{msg_prefix}。请在项目目录下对当前解释器执行："
        f' "{sys.executable}" -m pip install openai'
        "  然后完全重启 runserver。若使用虚拟环境，请先 activate 再安装。"
    )
    if _OPENAI_IMPORT_ERR:
        hint += f"（导入错误：{_OPENAI_IMPORT_ERR}）"
    return hint


# 智谱 OpenAI 兼容接口默认地址（不含路径时自动补全 /chat/completions）
ZHIPU_DEFAULT_CHAT_BASE = "https://open.bigmodel.cn/api/paas/v4"
IFLYTEK_MAAS_OPENAI_BASE = "https://maas-coding-api.cn-huabei-1.xf-yun.com/v1"
IFLYTEK_MAAS_CHAT_COMPLETIONS = (
    "https://maas-coding-api.cn-huabei-1.xf-yun.com/v1/chat/completions"
)
IFLYTEK_MAAS_MODEL_TYPE = "iflytek-spark-maas-coding"
IFLYTEK_MAAS_PAYLOAD_MODEL = "astron-code-latest"

SYSTEM_PROMPT = (
    "You are a software testing assistant. Upon receiving this connection test, "
    "simply reply: 'Connection successful, Zhipu AI is ready.'"
)


def _resolve_chat_completions_url(base_url: str, model: str) -> str:
    """
    若未填写 base_url：仅当 model 为智谱 GLM 系列时使用官方默认 host；
    否则必须由调用方提供 base_url（避免误请求智谱）。
    """
    raw = (base_url or "").strip()
    m = (model or "").strip().lower()
    is_glm = m.startswith("glm-") or m.startswith("glm4")
    if not raw:
        if is_glm:
            raw = ZHIPU_DEFAULT_CHAT_BASE
        else:
            return ""
    raw = raw.rstrip("/")
    if raw.endswith("/chat/completions"):
        return raw
    if "/chat/completions/" in raw or raw.endswith("/chat/completions"):
        return raw
    return f"{raw}/chat/completions"


def _resolve_openai_target(model: str, base_url: str):
    """
    统一解析 OpenAI 兼容目标：
    - 讯飞 MaaS Coding：强制 payload model；base_url 允许外部自定义，空值时给默认完整端点
    - 其他：保持用户/系统配置
    """
    m = (model or "").strip()
    b = (base_url or "").strip()
    if m == IFLYTEK_MAAS_MODEL_TYPE:
        if not b:
            b = IFLYTEK_MAAS_CHAT_COMPLETIONS
        return IFLYTEK_MAAS_PAYLOAD_MODEL, b
    return m, b


def _normalize_openai_sdk_base_url(base_url: str, model: str) -> str:
    """
    OpenAI Python SDK 期望 base_url 是“根路径”（如 .../v1），
    若传入了 .../chat/completions 会导致 SDK 再拼一次路径而 404。
    """
    raw = (base_url or "").strip().rstrip("/")
    if not raw:
        return raw
    if raw.endswith("/chat/completions"):
        raw = raw[: -len("/chat/completions")]
    # 讯飞模型兜底：若被裁成空或异常，回退到标准 /v1 根路径
    if model == IFLYTEK_MAAS_PAYLOAD_MODEL and not raw:
        return IFLYTEK_MAAS_OPENAI_BASE
    return raw


def _extract_reply(parsed: dict) -> str:
    choices = parsed.get("choices") or []
    if not choices:
        return ""
    msg = (choices[0] or {}).get("message") or {}
    return (msg.get("content") or "").strip()


class LlmTestConnectionAPIView(APIView):
    """
    代理「测试大模型连接」：前端传入 api_key / model / base_url（可选），
    服务端以 OpenAI Chat Completions 格式请求（智谱 v4 兼容）。
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        api_key = (request.data.get("api_key") or "").strip()
        model = (request.data.get("model") or "").strip()
        base_url = (request.data.get("base_url") or "").strip()
        model, base_url = _resolve_openai_target(model, base_url)

        if not api_key:
            return Response(
                {"code": 400, "msg": "API Key 不能为空", "data": None},
                status=200,
            )
        if not model:
            return Response(
                {"code": 400, "msg": "请选择模型类型", "data": None},
                status=200,
            )

        url = _resolve_chat_completions_url(base_url, model)
        _debug_log_openai_target("llm_test_connection_raw_http", model, url)
        if not url:
            return Response(
                {
                    "code": 400,
                    "msg": "当前模型需填写自定义 API 地址（Base URL）",
                    "data": None,
                },
                status=200,
            )

        body = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": "Connection test. Reply as instructed."},
            ],
            "max_tokens": 80,
            "temperature": 0.3,
        }
        body_bytes = json.dumps(body, ensure_ascii=False).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=body_bytes,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            },
        )
        ctx = ssl.create_default_context()

        try:
            with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
                raw = resp.read().decode("utf-8", errors="replace")
                parsed = json.loads(raw)
        except socket.timeout:
            return Response(
                {
                    "code": 400,
                    "msg": "连接超时，请检查网络、代理或稍后重试。",
                    "data": None,
                },
                status=200,
            )
        except urllib.error.HTTPError as e:
            err_text = e.read().decode("utf-8", errors="replace")
            try:
                err_json = json.loads(err_text)
                detail = err_json.get("error") or err_json.get("message") or err_text
                if isinstance(detail, dict):
                    detail = detail.get("message") or str(detail)
            except json.JSONDecodeError:
                detail = err_text[:500] or e.reason
            if e.code in (401, 403):
                return Response(
                    {
                        "code": 400,
                        "msg": f"鉴权失败（{e.code}）：请检查 API Key 是否有效。{detail}",
                        "data": None,
                    },
                    status=200,
                )
            return Response(
                {
                    "code": 400,
                    "msg": f"上游返回错误 {e.code}: {detail}",
                    "data": None,
                },
                status=200,
            )
        except urllib.error.URLError as e:
            reason = getattr(e, "reason", str(e))
            if isinstance(reason, TimeoutError) or "timed out" in str(e).lower():
                return Response(
                    {
                        "code": 400,
                        "msg": "连接超时，请检查网络或稍后重试。",
                        "data": None,
                    },
                    status=200,
                )
            return Response(
                {"code": 400, "msg": f"网络错误: {reason}", "data": None},
                status=200,
            )
        except json.JSONDecodeError:
            return Response(
                {"code": 400, "msg": "上游返回非 JSON，请确认 API 地址是否为 OpenAI 兼容的 Chat Completions。", "data": None},
                status=200,
            )
        except Exception as e:
            return Response(
                {"code": 400, "msg": f"请求异常: {str(e)}", "data": None},
                status=200,
            )

        reply = _extract_reply(parsed)
        if not reply and "error" in parsed:
            err = parsed["error"]
            msg = err if isinstance(err, str) else err.get("message", str(err))
            return Response(
                {"code": 400, "msg": f"模型接口报错: {msg}", "data": None},
                status=200,
            )

        return Response(
            {
                "code": 200,
                "msg": "连接成功",
                "data": {"reply": reply, "model": model},
            },
            status=200,
        )


ZHIPU_DEFAULT_API_BASE = "https://open.bigmodel.cn/api/paas/v4"


class AiTestConnectionAPIView(APIView):
    """
    POST /api/ai/test-connection/
    使用 OpenAI 官方 Python SDK 调用智谱等兼容端点，用于「测试连接」。
    Body: api_key (必填), model (可选，默认 glm-4.7-flash), api_base_url (可选)
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        api_key = (request.data.get("api_key") or "").strip()
        api_base_url = (
            request.data.get("api_base_url") or request.data.get("base_url") or ""
        ).strip()
        model = (request.data.get("model") or "").strip() or "glm-4.7-flash"
        model, api_base_url = _resolve_openai_target(model, api_base_url)
        api_base_url = _normalize_openai_sdk_base_url(api_base_url, model)

        def err_body(msg: str, status_code: int = 400):
            return Response(
                {
                    "success": False,
                    "message": msg,
                    "error": msg,
                    "reply": None,
                    "model": model,
                },
                status=status_code,
            )

        if not api_key:
            return err_body("API Key 不能为空")

        if not api_base_url:
            api_base_url = ZHIPU_DEFAULT_API_BASE
        api_base_url = api_base_url.rstrip("/")

        if not OPENAI_SDK_AVAILABLE:
            return err_body(_openai_missing_response_json())

        try:
            _debug_log_openai_target("ai_test_connection_sdk", model, api_base_url)
            client = OpenAI(api_key=api_key, base_url=api_base_url, timeout=20.0)
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": "Please reply 'Connection successful'.",
                    }
                ],
                max_tokens=80,
                temperature=0.2,
            )
            choice = completion.choices[0].message
            reply = (getattr(choice, "content", None) or "").strip()
        except AuthenticationError as e:
            logger.exception(
                "AI test connection auth failed. user_id=%s model=%s base_url=%s",
                getattr(request.user, "id", None),
                model,
                api_base_url,
            )
            return err_body(f"鉴权失败，请检查 API Key：{e}")
        except APITimeoutError:
            logger.exception(
                "AI test connection timeout. user_id=%s model=%s base_url=%s",
                getattr(request.user, "id", None),
                model,
                api_base_url,
            )
            return err_body("连接上游超时，请检查网络或代理后重试。", status_code=504)
        except APIConnectionError as e:
            logger.exception(
                "AI test connection upstream unreachable. user_id=%s model=%s base_url=%s",
                getattr(request.user, "id", None),
                model,
                api_base_url,
            )
            return err_body(f"无法连接模型服务：{e}", status_code=502)
        except APIError as e:
            logger.exception(
                "AI test connection API error. user_id=%s model=%s base_url=%s",
                getattr(request.user, "id", None),
                model,
                api_base_url,
            )
            return err_body(getattr(e, "message", None) or str(e), status_code=502)
        except Exception as e:
            logger.exception(
                "AI test connection unexpected exception. user_id=%s model=%s base_url=%s",
                getattr(request.user, "id", None),
                model,
                api_base_url,
            )
            return err_body(str(e), status_code=500)

        if not reply:
            return err_body("模型未返回有效内容，请检查 model 名称与账户权限。")

        return Response(
            {
                "success": True,
                "message": "连接成功",
                "error": None,
                "reply": reply,
                "model": model,
            },
            status=200,
        )


class AiVerifyConnectionAPIView(APIView):
    """
    POST /api/ai/verify-connection/
    专用连通性校验：仅依赖 api_key，固定智谱 v4 base_url 与 glm-4.7-flash。
    """

    permission_classes = [IsAuthenticated]

    _VERIFY_MODEL = "glm-4.7-flash"
    _VERIFY_BASE = "https://open.bigmodel.cn/api/paas/v4"
    _SYSTEM_PROMPT = "你是一个测试助手，请仅回复'连接成功'"

    def post(self, request):
        api_key = (request.data.get("api_key") or "").strip()
        model = self._VERIFY_MODEL

        def fail(msg: str, status_code: int = 400):
            return Response(
                {
                    "success": False,
                    "message": msg,
                    "error": msg,
                    "reply": None,
                    "model": model,
                },
                status=status_code,
            )

        if not api_key:
            return fail("API Key 不能为空")

        base_url = self._VERIFY_BASE.rstrip("/")
        base_url = _normalize_openai_sdk_base_url(base_url, model)

        if not OPENAI_SDK_AVAILABLE:
            return fail(_openai_missing_response_json())

        try:
            _debug_log_openai_target("ai_verify_connection_sdk", model, base_url)
            client = OpenAI(api_key=api_key, base_url=base_url, timeout=20.0)
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self._SYSTEM_PROMPT},
                    {"role": "user", "content": "测试连通性。"},
                ],
                max_tokens=60,
                temperature=0.1,
            )
            choice = completion.choices[0].message
            reply = (getattr(choice, "content", None) or "").strip()
        except AuthenticationError as e:
            logger.exception(
                "AI verify connection auth failed. user_id=%s model=%s base_url=%s",
                getattr(request.user, "id", None),
                model,
                base_url,
            )
            return fail(f"API Key 无效或未授权：{e}")
        except APITimeoutError:
            logger.exception(
                "AI verify connection timeout. user_id=%s model=%s base_url=%s",
                getattr(request.user, "id", None),
                model,
                base_url,
            )
            return fail("请求智谱接口超时，请检查网络或稍后重试。", status_code=504)
        except APIConnectionError as e:
            logger.exception(
                "AI verify connection upstream unreachable. user_id=%s model=%s base_url=%s",
                getattr(request.user, "id", None),
                model,
                base_url,
            )
            return fail(f"无法连接智谱服务：{e}", status_code=502)
        except APIError as e:
            logger.exception(
                "AI verify connection API error. user_id=%s model=%s base_url=%s",
                getattr(request.user, "id", None),
                model,
                base_url,
            )
            return fail(getattr(e, "message", None) or str(e), status_code=502)
        except Exception as e:
            logger.exception(
                "AI verify connection unexpected exception. user_id=%s model=%s base_url=%s",
                getattr(request.user, "id", None),
                model,
                base_url,
            )
            return fail(str(e), status_code=500)

        if not reply:
            return fail("模型未返回内容，请检查账号是否开通该模型。")

        return Response(
            {
                "success": True,
                "message": "连接成功",
                "error": None,
                "reply": reply,
                "model": model,
            },
            status=200,
        )


AI_GENERATE_MODEL = "glm-4.7-flash"
AI_GENERATE_CASES_MAX_TOKENS = max(4096, int(getattr(settings, "AI_GENERATE_CASES_MAX_TOKENS", 8192)))
AI_GENERATE_MIN_CASES = max(1, int(getattr(settings, "AI_GENERATE_MIN_CASES", 4)))
AI_GENERATE_MAX_CASES = max(AI_GENERATE_MIN_CASES, int(getattr(settings, "AI_GENERATE_MAX_CASES", 20)))
AI_GENERATE_RETRY_ROUNDS = max(0, int(getattr(settings, "AI_GENERATE_RETRY_ROUNDS", 2)))
AI_PHASE2_TIMEOUT_SECONDS = float(getattr(settings, "AI_PHASE2_TIMEOUT_SECONDS", 60.0))
AI_GENERATE_TOTAL_TIMEOUT_SECONDS = float(getattr(settings, "AI_GENERATE_TOTAL_TIMEOUT_SECONDS", 70.0))


def _get_active_ai_model_credentials():
    """库中全局 AI 配置且 is_connected 时返回 (api_key, base_url, model_type)，否则 (None, None, None)。"""
    try:
        from user.models import AIModelConfig
    except Exception:  # pragma: no cover
        return None, None, None
    row = AIModelConfig.objects.order_by("id").first()
    if not row or not row.is_connected:
        return None, None, None
    key = (row.api_key or "").strip()
    if not key:
        return None, None, None
    base = (row.base_url or "").strip() or ZHIPU_DEFAULT_API_BASE
    model = (row.model_type or "").strip() or AI_GENERATE_MODEL
    model, base = _resolve_openai_target(model, base)
    base = _normalize_openai_sdk_base_url(base, model)
    return key, base.rstrip("/"), model


_AI_TEST_TYPE_ALLOWED = frozenset(
    {"functional", "api", "performance", "security", "ui-automation"}
)

_AI_TEST_TYPE_FOCUS = {
    "functional": "功能/界面测试：用户流程、验收标准与端到端行为（生成内容须为简体中文）。",
    "api": "接口测试：端点、契约、状态码、请求体与校验、异常响应等（生成内容须为简体中文）。",
    "performance": "性能测试：负载/场景、时延与吞吐、压测与容量等（生成内容须为简体中文）。",
    "security": "安全测试：认证鉴权、注入、数据暴露与威胁角度等（生成内容须为简体中文）。",
    "ui-automation": "UI 自动化：定位策略、页面流转、等待与同步、数据驱动步骤与断言（生成内容须为简体中文）。",
}


def _normalize_context_data(raw) -> dict:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    return {}


def _normalize_ext_config(raw) -> dict:
    if raw is None:
        return {}
    if isinstance(raw, dict):
        return raw
    return {}


def _legacy_context_from_ext_config(ext: dict, test_type: str) -> dict:
    """将前端 ext_config 映射为旧版 context_data 合并键。"""
    tt = (test_type or "").strip()
    out: dict = {}
    if tt == "api" and (ext.get("api_spec") or "").strip():
        out["api_definition"] = (ext.get("api_spec") or "").strip()
    if tt == "functional":
        bf = (ext.get("business_flow") or "").strip()
        if bf:
            out["business_flow"] = bf
    if tt == "ui-automation" and (ext.get("ui_elements") or "").strip():
        out["ui_locators"] = (ext.get("ui_elements") or "").strip()
    if tt == "performance":
        pt = ext.get("perf_targets")
        if isinstance(pt, dict) and pt:
            try:
                out["performance_metrics"] = json.dumps(pt, ensure_ascii=False)
            except (TypeError, ValueError):
                out["performance_metrics"] = str(pt)
    if tt == "security":
        sv = ext.get("sec_vectors")
        if isinstance(sv, (list, tuple)) and sv:
            out["vulnerability_types"] = [str(x) for x in sv if str(x).strip()]
        if (ext.get("scan_scope") or "").strip():
            out["scan_scope"] = (ext.get("scan_scope") or "").strip()
        if (ext.get("risk_level") or "").strip():
            out["risk_level"] = (ext.get("risk_level") or "").strip()
    return out


def _merge_context_data_into_requirement(
    requirement: str, test_type: str, cd: dict
) -> str:
    """将 context_data 中的差异化字段拼入需求文本，供 LLM 用户消息与 RAG 使用。"""
    base = (requirement or "").strip()
    parts: list[str] = [base] if base else []
    if not cd:
        return base
    tt = (test_type or "").strip()
    if tt == "functional":
        bf = (cd.get("business_flow") or cd.get("preconditions") or "").strip()
        if bf:
            parts.append("【业务流程/前置条件】\n" + bf)
    elif tt == "ui-automation":
        ul = (cd.get("ui_locators") or "").strip()
        if ul:
            parts.append("【页面元素/定位参考】\n" + ul)
    elif tt == "performance":
        pm = (cd.get("performance_metrics") or "").strip()
        if pm:
            parts.append("【性能指标与约束】\n" + pm)
    elif tt == "security":
        vt = cd.get("vulnerability_types")
        if isinstance(vt, (list, tuple)) and vt:
            labs = ", ".join(str(x).strip() for x in vt if str(x).strip())
            if labs:
                parts.append("【关注漏洞类型】\n" + labs)
        ss = (cd.get("scan_scope") or "").strip()
        if ss:
            parts.append("【扫描/测试范围】\n" + ss)
        rl = (cd.get("risk_level") or "").strip()
        if rl:
            parts.append("【风险等级偏好】\n" + rl)
    return "\n\n".join(parts) if parts else base


def _prepare_ai_generate_context(request):
    """
    解析生成用例请求。成功返回 (ctx, None)，ctx 含 requirement / api_key / api_base_url / model_used；
    失败返回 (None, error_message)。
    """
    requirement = (
        request.data.get("prompt_text")
        or request.data.get("requirement")
        or request.data.get("requirement_description")
        or request.data.get("description")
        or ""
    ).strip()
    api_spec = (
        request.data.get("api_spec")
        or request.data.get("api_interface_doc")
        or request.data.get("openapi_spec")
        or ""
    )
    if isinstance(api_spec, str):
        api_spec = api_spec.strip()
    else:
        api_spec = ""

    context_data = _normalize_context_data(request.data.get("context_data"))
    ext_config = _normalize_ext_config(request.data.get("ext_config"))

    raw_tt_early = (
        request.data.get("testType") or request.data.get("test_type") or ""
    ).strip()
    test_type_early = (
        raw_tt_early if raw_tt_early in _AI_TEST_TYPE_ALLOWED else "functional"
    )

    if ext_config:
        context_data = {
            **context_data,
            **_legacy_context_from_ext_config(ext_config, test_type_early),
        }
    if not api_spec and ext_config.get("api_spec"):
        api_spec = str(ext_config.get("api_spec") or "").strip()

    api_from_ctx = (context_data.get("api_definition") or "").strip()
    if not api_spec and api_from_ctx:
        api_spec = api_from_ctx

    requirement = _merge_context_data_into_requirement(
        requirement, test_type_early, context_data
    )

    if not requirement and not api_spec:
        return None, "请填写需求描述，或在请求中附带接口定义（api_spec / OpenAPI 粘贴）"

    if not requirement and api_spec:
        requirement = (
            "请根据下方【接口定义原文】生成覆盖正向与典型异常场景的接口测试用例，"
            "并为每条用例分配 businessId（API-1 起递增）；"
            "每条须包含 method、url、headers、request_body、assert_logic。"
        )

    if test_type_early == "api" and api_spec:
        spec_ok, spec_err = validate_spec(api_spec)
        if not spec_ok:
            return None, spec_err or "接口定义格式无效"

    api_key = (request.data.get("api_key") or "").strip()
    custom_base = (
        request.data.get("api_base_url") or request.data.get("base_url") or ""
    ).strip()
    custom_model = (request.data.get("model") or "").strip()

    if api_key:
        api_base_url = (custom_base or ZHIPU_DEFAULT_API_BASE).rstrip("/")
        model_used = custom_model or AI_GENERATE_MODEL
        model_used, api_base_url = _resolve_openai_target(model_used, api_base_url)
        api_base_url = _normalize_openai_sdk_base_url(api_base_url, model_used)
    else:
        api_key, api_base_url, model_used = _get_active_ai_model_credentials()
        if not api_key:
            return None, (
                "缺少 API Key：请由系统管理员在「智能助手 → 模型接入」保存并连接模型，"
                "或在请求中传入 api_key"
            )
        api_base_url = (api_base_url or "").rstrip("/")
        if not model_used:
            model_used = AI_GENERATE_MODEL

    raw_mod = request.data.get("module_id")
    if raw_mod is None:
        raw_mod = request.data.get("module")
    module_id = None
    if raw_mod not in (None, ""):
        try:
            module_id = int(raw_mod)
        except (TypeError, ValueError):
            module_id = None

    module_name = (request.data.get("module_name") or "").strip()
    if module_id is not None and not module_name:
        try:
            from testcase.models import TestModule

            module_name = (
                TestModule.objects.filter(pk=module_id)
                .values_list("name", flat=True)
                .first()
                or ""
            )
        except Exception:  # pragma: no cover
            module_name = ""
    if not module_name:
        module_name = "（未指定模块，请仅围绕下方需求归纳模块名与用例；module_name 取值须用简体中文）"

    raw_tt = (
        request.data.get("testType") or request.data.get("test_type") or ""
    ).strip()
    test_type = raw_tt if raw_tt in _AI_TEST_TYPE_ALLOWED else "functional"
    test_type_focus = _AI_TEST_TYPE_FOCUS.get(
        test_type, _AI_TEST_TYPE_FOCUS["functional"]
    )

    rag_enabled = ext_config.get("is_rag_enabled", True)
    if rag_enabled is None:
        rag_enabled = True

    return (
        {
            "requirement": requirement,
            "api_spec": api_spec,
            "api_key": api_key,
            "api_base_url": api_base_url,
            "model_used": model_used,
            "module_id": module_id,
            "module_name": module_name,
            "test_type": test_type,
            "test_type_focus": test_type_focus,
            "context_data": context_data,
            "ext_config": ext_config,
            "rag_enabled": bool(rag_enabled),
        },
        None,
    )


def _sse_event(obj: dict) -> bytes:
    """
    SSE 单条事件：一行 data 字段 + 空行结束（RFC 要求以 \\n\\n 分隔事件）。
    JSON 单行输出，避免 data 内未转义换行破坏帧边界。
    """
    payload = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    return f"data: {payload}\n\n".encode("utf-8")


_ZH_JSON_LANGUAGE_MANDATE = """
══════════════════════════════════════════════════════
【语言强制 · 必须遵守】
你是一名专业软件测试工程师，根据用户需求生成测试用例。
【输出形态 · 最高优先级】只输出「纯 JSON 数组」这一段文本本身：
- 第一个字符必须是 [ ，最后一个字符必须是 ] ；
- 严禁使用 ``` 或 ```json 等 Markdown 代码围栏；
- 严禁在 JSON 前后输出任何解释、标题、注释或「以下是结果」类话术；
- 严禁输出除该 JSON 数组以外的任意字符（含空行前的说明）。
JSON 内所有**字符串取值**（caseName、precondition、steps、expectedResult、module_name 等字段的**值**）
必须**全部使用简体中文**撰写；不要用英文撰写用例标题、步骤或预期（禁止整句英文描述）。
JSON **键名**必须严格为下列 schema（camelCase / module_name），不得改为中文键名。
允许保留必要的技术拉丁片段（例如 URL 路径、HTTP 方法字面值、错误码数字），但解释性文字一律用中文。

[MANDATORY — English summary for the model]
You are a professional software testing engineer. Output strictly a JSON array only.
ALL human-readable string VALUES (caseName, precondition, steps, expectedResult, module_name, etc.)
MUST be entirely in Simplified Chinese (简体中文). Do not use English for these values.
JSON key names MUST remain exactly as specified below.
══════════════════════════════════════════════════════
"""

_AI_GENERATE_SYSTEM_TEMPLATE = (
    _ZH_JSON_LANGUAGE_MANDATE
    + """You are an Expert Software Test Automation Engineer. Generate comprehensive, highly detailed, and strictly independent test cases based on [Current Module] and [Requirement Description]. All natural-language content you produce inside JSON MUST be in Simplified Chinese as mandated above.

【STRICT CONSTRAINTS & RULES】

1. Strict Module Isolation (Zero Leakage):
   Focus EXCLUSIVELY on [Current Module]. If the module is «登录», do NOT generate cases for «注册» or unrelated menus. Preconditions must be written in Chinese (e.g. 「系统中已存在测试账号 admin，密码为 Abc!234」).

2. Ultra-Granular Details (简体中文):
   - 前置条件：具体、可执行。
   - 测试数据：具体账号、密码、输入值等，避免抽象表述。
   - 步骤：编号、可操作的界面或接口动作描述（中文）。
   - 预期结果：同时写清前端表现与后端/系统状态（中文）。

3. Deduplication & Similarity (CRITICAL):
   - 用例之间不得语义高度重复；自相检查后删除冗余场景。

4. Coverage:
   - 恰好一条主流程正向用例 level P0；若干负向/边界 P1/P2；除非需求明确，少用 P3。

5. RAG（当系统消息后文出现 Highly Relevant Existing Cases 时）：
   - 若已有用例已完全覆盖需求：仅输出字面量 [ALL_COVERED]，勿输出 JSON。
   - 否则仅输出填补缺口的新用例 JSON 数组。

【INPUT CONTEXT】
测试类型侧重点（用例内容须与此一致且为中文）：{test_type_focus}
当前模块（module_name 取值须与之对齐，中文）: {module_name}
需求描述（可能是中文）:
{requirement_description}

（可选）RAG：下文 Highly Relevant Existing Cases 为向量检索参考，用于去重与缺口分析，且其中片段若为英文仅供参考，你生成的新用例正文仍须中文。

【OUTPUT FORMAT】
仅输出合法 JSON 数组（纯文本，无任何 Markdown 包裹、无前后缀说明）。键名必须完全一致：
[
  {{
    "caseName": "简明中文用例标题，概括本场景",
    "level": "P0",
    "precondition": "中文：详细前置条件",
    "steps": "1. 第一步（中文）\\n2. 第二步（中文）",
    "expectedResult": "中文：界面表现与后端状态的预期",
    "module_name": "与上文「当前模块」一致的中文字符串（若模块为占位说明则从需求推断简短中文模块名）"
  }}
]

说明：导入接口需要 module_name 与系统匹配；服务端会做相似度去重（caseName+steps 等），请尽量减少冗余。
再次强调：不要输出 ```json 或 ```，不要输出数组外的任何文字。

规模：通常 1 条 P0 + 若干 P1/P2（合计约 5～12 条）；需求很小时至少 3 条且含必填 P0。"""
)

_PHASE1_INTENT_SYSTEM_PROMPT = """
你是一名高级测试架构师。请根据用户一句话需求，推导最可能的业务模块并提炼关键测试点。
你必须严格输出 JSON 对象，不得输出任何额外说明、Markdown 或代码块。
输出格式必须为：
{
  "module_name": "中文模块名称",
  "key_test_points": ["测试点1", "测试点2", "测试点3"]
}
要求：
1) module_name 必须是简体中文，简短明确（例如：支付中心、购物车模块、订单管理）。
2) key_test_points 必须为数组，元素为简体中文短句，建议 3~8 条。
3) 禁止输出 JSON 以外内容。
""".strip()

_PHASE1_REPAIR_SYSTEM_PROMPT = """
你是 JSON 修复助手。请将输入内容修复为严格 JSON 对象，且仅输出 JSON 本体。
JSON 结构固定为：
{
  "module_name": "中文模块名称",
  "key_test_points": ["测试点1", "测试点2"]
}
""".strip()

_PHASE2_MULTI_CASE_MANDATE = """
【Phase 2 强制生成规则（最高优先级）】
你是一个高级测试工程师。你必须严格遵循用户的需求描述，生成一个包含多条用例的列表。
禁止只生成正向用例，必须包含正向、异常、边界值等场景。

输出必须是 JSON Array，至少 4 条（若需求明显复杂可更多），每个元素至少包含：
[
  {
    "name": "用例名称",
    "type": "正向/异常/边界",
    "caseName": "与 name 语义一致的中文标题",
    "level": "P0/P1/P2/P3",
    "precondition": "前置条件",
    "steps": "步骤",
    "expectedResult": "预期结果",
    "module_name": "模块名"
  }
]
严禁返回单对象，严禁返回非数组，严禁数组为空。
""".strip()


def _build_ai_generate_system_prompt(
    module_name: str,
    requirement: str,
    test_type_focus: str | None = None,
) -> str:
    """Fill module and requirement into the expert system template."""
    mn = (module_name or "").strip() or "（未指定模块，请仅围绕需求归纳；module_name 须为简体中文）"
    focus = (test_type_focus or _AI_TEST_TYPE_FOCUS["functional"]).strip()
    return _AI_GENERATE_SYSTEM_TEMPLATE.format(
        test_type_focus=focus,
        module_name=mn,
        requirement_description=(requirement or "").strip(),
    )


def _rag_requirement_text(ctx: dict) -> str:
    """RAG 嵌入用文本：需求 + 接口定义摘录，便于相似用例检索。"""
    base = (ctx.get("requirement") or "").strip()
    spec = (ctx.get("api_spec") or "").strip()
    if not spec:
        return base
    clip = spec[:12000] if len(spec) > 12000 else spec
    return base + "\n\n【接口定义原文摘录】\n" + clip


def _extract_json_object_payload(raw_text: str) -> str | None:
    text = _strip_code_fences((raw_text or "").strip())
    if not text:
        return None
    md = re.search(r"\{[\s\S]*\}", text)
    if md:
        return (md.group(0) or "").strip()
    return None


def _parse_phase1_json(raw_text: str) -> dict | None:
    payload = _extract_json_object_payload(raw_text)
    if not payload:
        return None
    try:
        data = json.loads(payload)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    module_name = str(data.get("module_name") or "").strip()
    points = data.get("key_test_points")
    if isinstance(points, str):
        points = [x.strip() for x in points.split("\n") if x.strip()]
    if not isinstance(points, list):
        points = []
    norm_points = [str(x).strip() for x in points if str(x).strip()]
    return {
        "module_name": module_name,
        "key_test_points": norm_points[:12],
    }


def _phase1_fallback(requirement: str, fallback_module: str = "") -> dict:
    req = (requirement or "").strip()
    mod = (fallback_module or "").strip() or "通用功能模块"
    points = []
    if req:
        points.append(f"围绕“{req[:40]}”的主流程验证")
        points.append("关键边界值与异常输入校验")
        points.append("接口/状态一致性与错误处理验证")
    return {"module_name": mod, "key_test_points": points}


def _run_phase1_intent_analysis(client, model_used: str, requirement: str, fallback_module: str = "") -> dict:
    user_prompt = "用户需求如下：\n" + (requirement or "").strip()
    try:
        phase1_resp = client.chat.completions.create(
            model=model_used,
            messages=[
                {"role": "system", "content": _PHASE1_INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=600,
        )
        raw_phase1 = (phase1_resp.choices[0].message.content or "").strip()
        parsed = _parse_phase1_json(raw_phase1)
        if parsed:
            if not parsed["module_name"]:
                parsed["module_name"] = (fallback_module or "").strip() or "通用功能模块"
            return parsed
        # 一次修复重试：让模型把上次文本纠正为合法 JSON
        repair_resp = client.chat.completions.create(
            model=model_used,
            messages=[
                {"role": "system", "content": _PHASE1_REPAIR_SYSTEM_PROMPT},
                {"role": "user", "content": raw_phase1[:6000]},
            ],
            temperature=0.0,
            max_tokens=400,
        )
        repaired = (repair_resp.choices[0].message.content or "").strip()
        parsed2 = _parse_phase1_json(repaired)
        if parsed2:
            if not parsed2["module_name"]:
                parsed2["module_name"] = (fallback_module or "").strip() or "通用功能模块"
            return parsed2
        logger.warning("Phase1 JSON 解析失败，已降级。raw=%s", raw_phase1[:500])
    except Exception:
        logger.exception("Phase1 意图识别异常，已降级 fallback")
    return _phase1_fallback(requirement=requirement, fallback_module=fallback_module)


def _phase1_analysis_block(phase1: dict) -> str:
    module_name = str(phase1.get("module_name") or "通用功能模块").strip()
    pts = phase1.get("key_test_points")
    if not isinstance(pts, list):
        pts = []
    lines = [f"- {str(x).strip()}" for x in pts if str(x).strip()]
    points_text = "\n".join(lines) if lines else "- （暂无，按需求进行通用测试点覆盖）"
    return (
        "## Phase 1 Analysis (Intent Inference)\n"
        f"- inferred_module_name: {module_name}\n"
        f"- key_test_points:\n{points_text}"
    )


def _phase1_query_text(requirement: str, phase1: dict, api_spec: str = "") -> str:
    mod = str(phase1.get("module_name") or "").strip()
    pts = phase1.get("key_test_points")
    if not isinstance(pts, list):
        pts = []
    pt_text = "；".join(str(x).strip() for x in pts if str(x).strip())
    parts = [x for x in [mod, (requirement or "").strip(), pt_text] if x]
    q = "\n".join(parts)
    spec = (api_spec or "").strip()
    if spec:
        q += "\n\n【接口定义原文摘录】\n" + (spec[:6000] + ("...(truncated)" if len(spec) > 6000 else ""))
    return q.strip()


def _strip_code_fences(text: str) -> str:
    text = (text or "").strip()
    if not text.startswith("```"):
        return text
    lines = text.split("\n")
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip().startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip()


def _sanitize_llm_json_text(text: str) -> str:
    """
    清理模型输出中的 Markdown JSON 标记，尽量保留纯 JSON 文本。
    """
    raw = (text or "").strip()
    if not raw:
        return raw
    cleaned = re.sub(r"```(?:json)?", "", raw, flags=re.IGNORECASE)
    cleaned = cleaned.replace("```", "")
    return cleaned.strip()


def _extract_json_payload_segment(raw_content: str) -> str | None:
    """
    从模型文本中尽可能提取 JSON 核心段：
    1) 优先提取 ```json ... ``` 代码块内容
    2) 回退到首个 [/{ 到最后 ]/} 的区间
    """
    text = _sanitize_llm_json_text((raw_content or "").strip())
    if not text:
        return None
    md = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    if md:
        inner = (md.group(1) or "").strip()
        if inner:
            return inner
    left_candidates = [i for i in (text.find("["), text.find("{")) if i >= 0]
    if not left_candidates:
        return None
    start = min(left_candidates)
    right_arr = text.rfind("]")
    right_obj = text.rfind("}")
    end = max(right_arr, right_obj)
    if end <= start:
        return None
    return text[start : end + 1].strip()


def _extract_json_array_span(raw_content: str) -> str | None:
    """取首个 '[' 与最后一个 ']' 之间的内容（含括号），用于截断/脏前缀时的兜底提取。"""
    text = _sanitize_llm_json_text(_strip_code_fences((raw_content or "").strip()))
    if not text:
        return None
    left = text.find("[")
    right = text.rfind("]")
    if left < 0 or right <= left:
        return None
    return text[left : right + 1].strip()


def _cases_list_from_parsed(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        inner = (
            data.get("cases")
            or data.get("test_cases")
            or data.get("items")
            or data.get("results")
            or data.get("data")
        )
        if isinstance(inner, list):
            return inner
    return None


def _try_json_load_cases_list(payload: str):
    try:
        data = json.loads(_sanitize_llm_json_text(payload))
    except json.JSONDecodeError:
        return None
    return _cases_list_from_parsed(data)


def _parse_json_array_with_bracket_balance(payload: str):
    """
    在因 max_tokens/网络截断导致末尾缺 `}` `]` 时，按括号计数简单补全后重试解析。
    不解析字符串内的括号，属启发式修复。
    """
    trial = (payload or "").strip()
    if not trial.startswith("["):
        return None
    for _ in range(64):
        got = _try_json_load_cases_list(trial)
        if got is not None:
            return got
        open_curly = trial.count("{")
        close_curly = trial.count("}")
        open_sq = trial.count("[")
        close_sq = trial.count("]")
        if open_curly > close_curly:
            trial += "}"
        elif open_sq > close_sq:
            trial += "]"
        else:
            break
    return None


def _parse_ai_cases_json(raw_content: str):
    """Return list[dict] or None if parsing fails."""
    raw_stripped = _strip_code_fences((raw_content or "").strip())
    candidates: list[str] = []
    if raw_stripped:
        candidates.append(raw_stripped)
    seg_payload = _extract_json_payload_segment(raw_stripped)
    if seg_payload and seg_payload not in candidates:
        candidates.append(seg_payload)
    arr_span = _extract_json_array_span(raw_content)
    if arr_span and arr_span not in candidates:
        candidates.append(arr_span)

    for cand in candidates:
        got = _try_json_load_cases_list(cand)
        if got is not None:
            return got

    for cand in candidates:
        got = _parse_json_array_with_bracket_balance(cand)
        if got is not None:
            return got

    if arr_span:
        got = _parse_json_array_with_bracket_balance(_strip_code_fences(arr_span))
        if got is not None:
            return got

    return None


def _normalize_generated_case(item, index: int, test_type: str | None = None):
    if not isinstance(item, dict):
        return None
    name = (
        item.get("case_name")
        or item.get("caseName")
        or item.get("name")
        or f"AI生成用例-{index + 1}"
    )
    name = str(name).strip()[:255] or f"AI生成用例-{index + 1}"
    level = str(item.get("level") or "P2").strip().upper()
    if level not in ("P0", "P1", "P2", "P3"):
        level = "P2"
    pre = str(item.get("precondition") or item.get("pre_condition") or "").strip()
    steps = str(item.get("steps") or item.get("step") or "").strip()
    exp = str(
        item.get("expected_result")
        or item.get("expectedResult")
        or item.get("expected")
        or ""
    ).strip()
    mod = str(
        item.get("module_name")
        or item.get("moduleName")
        or item.get("belonging_module")
        or item.get("所属模块")
        or ""
    ).strip()[:100]

    tt = (test_type or "").strip()
    risk_level = ""
    attack_surface = ""
    tool_preset = ""
    if tt == "security":
        av = item.get("attackVector") or item.get("attack_vector")
        pe = item.get("payloadExample") or item.get("payload_example")
        tsteps = item.get("testSteps") or item.get("test_steps")
        ed = item.get("expectedDefense") or item.get("expected_defense")
        rl_raw = item.get("riskLevel") or item.get("risk_level") or ""
        rl = str(rl_raw).strip()
        if rl not in ("高", "中", "低"):
            rl = ""
        risk_level = rl
        if not steps and (av or tsteps or pe):
            chunks = []
            if av:
                chunks.append(f"【攻击向量】{str(av).strip()}")
            if tsteps:
                chunks.append(f"【测试步骤】{str(tsteps).strip()}")
            if pe:
                chunks.append(f"【Payload 示例】{str(pe).strip()}")
            steps = "\n".join(chunks)
        if not exp and ed:
            exp = str(ed).strip()
        attack_surface = (str(av).strip() if av else "")[:512]
        if not attack_surface and steps:
            attack_surface = steps[:512]
        tool_preset = f"risk_level:{risk_level}" if risk_level else ""

    row = {
        "case_name": name,
        "level": level,
        "precondition": pre,
        "steps": steps,
        "expected_result": exp,
        "module_name": mod,
    }
    if tt == "security":
        row["risk_level"] = risk_level
        row["attack_surface"] = attack_surface
        row["tool_preset"] = tool_preset
    return row


def _deduplicate_cases_with_guard(cases: list[dict], log_prefix: str) -> list[dict]:
    raw_case_count = len(cases)
    dedup_cases = deduplicate_generated_cases(cases)
    if raw_case_count >= 2 and len(dedup_cases) <= 1:
        logger.warning(
            "%s 去重疑似过度，保留原始结果。raw=%s dedup=%s",
            log_prefix,
            raw_case_count,
            len(dedup_cases),
        )
        return cases
    return dedup_cases


def _expand_cases_to_minimum_if_needed(
    *,
    client,
    model_used: str,
    phase2_system_prompt: str,
    user_msg: str,
    cases: list[dict],
    min_cases: int,
    test_type: str | None = None,
    use_api: bool = False,
) -> list[dict]:
    min_cases = max(1, int(min_cases))
    if len(cases) >= min_cases:
        return cases
    needed = min_cases - len(cases)
    brief_names = [str(x.get("case_name") or "").strip() for x in cases[:20] if isinstance(x, dict)]
    existing_hint = "\n".join(f"- {x}" for x in brief_names if x) or "- （暂无）"
    supplement_user = (
        user_msg
        + "\n\n【补生成任务】\n"
        + f"当前仅有 {len(cases)} 条，请补充至少 {needed} 条“新增且不重复”的用例。\n"
        + "新增用例必须覆盖异常/边界，禁止只补正向。\n"
        + "仅输出 JSON 数组（只包含新增项）。\n"
        + "已有用例标题（避免重复）：\n"
        + existing_hint
    )
    try:
        completion = client.chat.completions.create(
            model=model_used,
            messages=[
                {"role": "system", "content": phase2_system_prompt},
                {"role": "user", "content": supplement_user},
            ],
            temperature=0.35,
            max_tokens=AI_GENERATE_CASES_MAX_TOKENS,
            timeout=AI_PHASE2_TIMEOUT_SECONDS,
        )
        raw = _sanitize_llm_json_text((completion.choices[0].message.content or "").strip())
        parsed = _parse_ai_cases_json(raw)
        if not parsed:
            return cases
        extra_cases = []
        for i, row in enumerate(parsed):
            norm = _normalize_generated_case(row, len(cases) + i, test_type)
            if norm:
                if use_api:
                    norm = enrich_normalized_case_with_api_fields(norm, row, len(cases) + i)
                extra_cases.append(norm)
        if not extra_cases:
            return cases
        merged = cases + extra_cases
        merged = _deduplicate_cases_with_guard(merged, "补生成结果")
        if use_api and merged:
            renumber_api_business_ids(merged)
        return merged
    except Exception:
        logger.exception("补生成最小条数失败，保留首轮结果")
        return cases


def _enforce_cases_cap(cases: list[dict], max_cases: int) -> list[dict]:
    cap = max(1, int(max_cases))
    if len(cases) <= cap:
        return cases
    return cases[:cap]


class AiGenerateCasesAPIView(APIView):
    """
    POST /api/ai/generate-cases/
    Body: requirement (必填), 可选 api_key / api_base_url（未传 Key 时用库中全局配置）
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        started_at = time.monotonic()

        def fail(msg: str, status_code=400, code: str = "BAD_REQUEST"):
            return Response(
                {
                    "status": "error",
                    "code": code,
                    "success": False,
                    "error": msg,
                    "cases": [],
                    "message": msg,
                },
                status=status_code,
            )

        def timeout_guard():
            elapsed = time.monotonic() - started_at
            if elapsed > AI_GENERATE_TOTAL_TIMEOUT_SECONDS:
                return fail(
                    "大模型生成超时或格式错误",
                    status_code=500,
                    code="GENERATION_TIMEOUT",
                )
            return None

        ctx, err = _prepare_ai_generate_context(request)
        if err:
            return fail(err, status_code=400, code="INVALID_INPUT")

        if not OPENAI_SDK_AVAILABLE:
            return fail(_openai_missing_response_json(), status_code=503, code="SDK_NOT_AVAILABLE")

        guard_result = timeout_guard()
        if guard_result is not None:
            return guard_result

        api_key = ctx["api_key"]
        api_base_url = ctx["api_base_url"]
        model_used = ctx["model_used"]
        module_id = ctx.get("module_id")
        disp = dispatch_ai_generation(ctx)
        use_api = disp.should_enrich_api
        user_msg = disp.user_message

        domain_system = apply_test_type_domain_strategy(disp.system_prompt, ctx)
        engine_addon = build_engine_addon(ctx)
        if engine_addon:
            domain_system = domain_system + "\n\n" + engine_addon

        try:
            _debug_log_openai_target("ai_generate_cases_sync_sdk", model_used, api_base_url)
            client = OpenAI(api_key=api_key, base_url=api_base_url, timeout=120.0)
            phase1 = _run_phase1_intent_analysis(
                client,
                model_used=model_used,
                requirement=str(ctx.get("requirement") or ""),
                fallback_module=str(ctx.get("module_name") or ""),
            )
            phase1_module = str(phase1.get("module_name") or "").strip() or str(ctx.get("module_name") or "")
            phase1_require = _phase1_query_text(
                requirement=str(ctx.get("requirement") or ""),
                phase1=phase1,
                api_spec=str(ctx.get("api_spec") or ""),
            )
            phase1_block = _phase1_analysis_block(phase1)
            domain_system_with_phase1 = domain_system + "\n\n" + phase1_block
            guard_result = timeout_guard()
            if guard_result is not None:
                return guard_result
            if ctx.get("rag_enabled", True):
                rag_top_k = max(1, int(getattr(settings, "RAG_TOP_K", 5)))
                system_prompt = build_rag_system_prompt(
                    domain_system_with_phase1,
                    phase1_require,
                    module_name=phase1_module,
                    api_spec=ctx.get("api_spec"),
                    top_k=rag_top_k,
                )
            else:
                system_prompt = domain_system_with_phase1
            phase2_system_prompt = system_prompt + "\n\n" + _PHASE2_MULTI_CASE_MANDATE

            # 生成前规避：读取模块已有标题，注入批量生成 Prompt，降低意图重复概率
            existing_rows: list[dict] = []
            existing_titles: list[str] = []
            try:
                from testcase.models import TestCase

                existing_qs = TestCase.objects.filter(is_deleted=False)
                if module_id:
                    existing_qs = existing_qs.filter(module_id=module_id)
                existing_rows = list(existing_qs.values("case_name"))
                existing_titles = [
                    str(x.get("case_name") or "").strip()
                    for x in existing_rows
                    if str(x.get("case_name") or "").strip()
                ]
            except Exception:
                logger.exception("读取已有用例失败，跳过前置规避提示")

            batch_user_prompt = build_batch_generation_prompt(
                module_name=str(ctx.get("module_name") or ""),
                requirement=str(ctx.get("requirement") or ""),
                test_type_focus=str(ctx.get("test_type_focus") or ""),
                existing_titles=existing_titles,
                min_count=max(5, AI_GENERATE_MIN_CASES),
            )
            try:
                try:
                    completion = client.chat.completions.create(
                        model=model_used,
                        messages=[
                            {"role": "system", "content": phase2_system_prompt},
                            {"role": "user", "content": batch_user_prompt},
                        ],
                        temperature=0.35,
                        max_tokens=AI_GENERATE_CASES_MAX_TOKENS,
                        timeout=AI_PHASE2_TIMEOUT_SECONDS,
                        response_format={"type": "json_object"},
                    )
                except Exception:
                    # 兼容部分 OpenAI 兼容端不支持 response_format 的情况
                    completion = client.chat.completions.create(
                        model=model_used,
                        messages=[
                            {"role": "system", "content": phase2_system_prompt},
                            {"role": "user", "content": batch_user_prompt},
                        ],
                        temperature=0.35,
                        max_tokens=AI_GENERATE_CASES_MAX_TOKENS,
                        timeout=AI_PHASE2_TIMEOUT_SECONDS,
                    )
                raw = _sanitize_llm_json_text((completion.choices[0].message.content or "").strip())
                try:
                    parsed = parse_batch_json_array(raw)
                except Exception:
                    # JSON Mode 兼容性不足时，回退到旧解析器，提升稳定性
                    parsed = _parse_ai_cases_json(raw)
                if not parsed:
                    snippet = raw[:400] + ("…" if len(raw) > 400 else "")
                    return fail(
                        f"大模型生成超时或格式错误：模型返回内容无法解析为 JSON 数组。片段：{snippet}",
                        status_code=400,
                        code="INVALID_JSON",
                    )

                cases = []
                for i, row in enumerate(parsed):
                    norm = _normalize_generated_case(
                        normalize_batch_case_item(row, i), i, ctx.get("test_type")
                    )
                    if norm:
                        if use_api:
                            norm = enrich_normalized_case_with_api_fields(norm, row, i)
                        cases.append(norm)

                cases = _deduplicate_cases_with_guard(cases, "生成结果")
                # 生成后语义去重：与数据库已有用例做向量相似度过滤
                existing_for_semantic = [
                    {"case_name": x.get("case_name") or "", "steps": ""}
                    for x in existing_rows
                ]
                cases = semantic_deduplicate_cases(
                    cases,
                    existing_for_semantic,
                    api_key=api_key,
                    base_url=api_base_url,
                )
                retry_round = 0
                while len(cases) < AI_GENERATE_MIN_CASES and retry_round < AI_GENERATE_RETRY_ROUNDS:
                    retry_round += 1
                    cases = _expand_cases_to_minimum_if_needed(
                        client=client,
                        model_used=model_used,
                        phase2_system_prompt=phase2_system_prompt,
                        user_msg=user_msg,
                        cases=cases,
                        min_cases=AI_GENERATE_MIN_CASES,
                        test_type=ctx.get("test_type"),
                        use_api=use_api,
                    )
                cases = _enforce_cases_cap(cases, AI_GENERATE_MAX_CASES)
                if use_api and cases:
                    renumber_api_business_ids(cases)

                if not cases:
                    return fail(
                        "大模型生成超时或格式错误：解析后没有有效用例。",
                        status_code=400,
                        code="INVALID_CASES",
                    )
            except APITimeoutError:
                logger.exception(
                    "AI generate cases phase2 timeout. user_id=%s model=%s base_url=%s module_id=%s",
                    getattr(request.user, "id", None),
                    model_used,
                    api_base_url,
                    module_id,
                )
                return fail("大模型生成超时或格式错误", status_code=500, code="PHASE2_TIMEOUT")
            except Exception as phase2_error:
                logger.exception(
                    "AI generate cases phase2 failed. user_id=%s model=%s base_url=%s module_id=%s err=%s",
                    getattr(request.user, "id", None),
                    model_used,
                    api_base_url,
                    module_id,
                    phase2_error,
                )
                return fail("大模型生成超时或格式错误", status_code=500, code="PHASE2_FAILED")
        except AuthenticationError as e:
            logger.exception(
                "AI generate cases auth failed. user_id=%s model=%s base_url=%s module_id=%s",
                getattr(request.user, "id", None),
                model_used,
                api_base_url,
                module_id,
            )
            return fail(f"API Key 无效：{e}", status_code=401, code="AUTH_ERROR")
        except APITimeoutError:
            logger.exception(
                "AI generate cases timeout. user_id=%s model=%s base_url=%s module_id=%s",
                getattr(request.user, "id", None),
                model_used,
                api_base_url,
                module_id,
            )
            return fail("调用智谱接口超时，请稍后重试。", status_code=504, code="UPSTREAM_TIMEOUT")
        except APIConnectionError as e:
            logger.exception(
                "AI generate cases upstream unreachable. user_id=%s model=%s base_url=%s module_id=%s",
                getattr(request.user, "id", None),
                model_used,
                api_base_url,
                module_id,
            )
            return fail(f"无法连接模型服务：{e}", status_code=502, code="UPSTREAM_UNREACHABLE")
        except APIError as e:
            logger.exception(
                "AI generate cases API error. user_id=%s model=%s base_url=%s module_id=%s",
                getattr(request.user, "id", None),
                model_used,
                api_base_url,
                module_id,
            )
            return fail(
                getattr(e, "message", None) or str(e),
                status_code=502,
                code="UPSTREAM_API_ERROR",
            )
        except Exception as e:
            logger.exception(
                "AI generate cases unexpected exception. user_id=%s model=%s base_url=%s module_id=%s",
                getattr(request.user, "id", None),
                model_used,
                api_base_url,
                module_id,
            )
            return fail(str(e), status_code=500, code="UNEXPECTED_ERROR")

        if is_all_covered_output(raw):
            return Response(
                {
                    "success": True,
                    "all_covered": True,
                    "phase1_analysis": phase1,
                    "error": None,
                    "cases": [],
                    "message": "语义检索：当前模块下已有用例已覆盖该需求，无需生成新用例。",
                    "model": model_used,
                },
                status=200,
            )

        guard_result = timeout_guard()
        if guard_result is not None:
            return guard_result

        return Response(
            {
                "success": True,
                "phase1_analysis": phase1,
                "error": None,
                "message": f"已生成 {len(cases)} 条用例",
                "cases": cases,
                "model": model_used,
            },
            status=200,
        )


@method_decorator(csrf_exempt, name="dispatch")
class AiGenerateCasesStreamView(View):
    """
    POST /api/ai/generate-cases-stream/
    使用标准 Django View（非 DRF APIView），避免 Accept: text/event-stream 触发 DRF 内容协商返回 406。
    鉴权仍与 DRF Token 一致；请求体通过 DRF Request + JSONParser 解析以复用 _prepare_ai_generate_context。
    """

    http_method_names = ["post", "options", "head"]

    def post(self, request, *args, **kwargs):
        drf_request = Request(request, parsers=[JSONParser()])
        try:
            auth_result = TokenAuthentication().authenticate(drf_request)
        except drf_exceptions.AuthenticationFailed as e:
            detail = e.detail
            if isinstance(detail, (list, dict)):
                return JsonResponse({"detail": detail}, status=401)
            return JsonResponse({"detail": str(detail)}, status=401)
        if auth_result is None:
            return JsonResponse(
                {"detail": "身份认证信息未提供。"},
                status=401,
            )
        user, token = auth_result
        drf_request.user = user
        drf_request.auth = token

        try:
            ctx, err = _prepare_ai_generate_context(drf_request)
        except drf_exceptions.ParseError:
            logger.exception(
                "AI stream request parse error. user_id=%s path=%s content_type=%s",
                getattr(getattr(drf_request, "user", None), "id", None),
                request.path,
                request.META.get("CONTENT_TYPE"),
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": "请求体解析失败，请确认 Content-Type 为 application/json 且 JSON 格式合法。",
                    "cases": [],
                    "message": "请求体解析失败",
                },
                status=400,
            )
        except Exception:
            logger.exception(
                "AI stream preflight unexpected error. user_id=%s path=%s",
                getattr(getattr(drf_request, "user", None), "id", None),
                request.path,
            )
            return JsonResponse(
                {
                    "success": False,
                    "error": "服务端预处理异常，请查看后端日志 traceback。",
                    "cases": [],
                    "message": "服务端预处理异常",
                },
                status=500,
            )
        if err:
            return JsonResponse(
                {"success": False, "error": err, "cases": [], "message": err},
                status=400,
            )

        if not OPENAI_SDK_AVAILABLE:
            return JsonResponse(
                {
                    "success": False,
                    "error": _openai_missing_response_json(),
                    "cases": [],
                    "message": _openai_missing_response_json(),
                },
                status=503,
            )

        api_key = ctx["api_key"]
        api_base_url = ctx["api_base_url"]
        model_used = ctx["model_used"]
        module_id = ctx.get("module_id")
        disp = dispatch_ai_generation(ctx)
        use_api = disp.should_enrich_api
        user_msg = disp.user_message

        def event_stream():
            # 首包立即下发，降低「首字等待」感知；不经过上游模型（本项目的 MIDDLEWARE 未启用 GZipMiddleware）。
            yield _sse_event(
                {
                    "type": "connected",
                    "message": "已连接，正在请求模型…",
                    "model": model_used,
                }
            )
            # 两阶段工作流：Phase1 意图识别 -> RAG 检索 -> Phase2 生成。
            domain_system = apply_test_type_domain_strategy(disp.system_prompt, ctx)
            engine_addon = build_engine_addon(ctx)
            if engine_addon:
                domain_system = domain_system + "\n\n" + engine_addon
            phase1 = _phase1_fallback(
                requirement=str(ctx.get("requirement") or ""),
                fallback_module=str(ctx.get("module_name") or ""),
            )
            phase1_module_name = str(ctx.get("module_name") or "")
            phase1_query = _rag_requirement_text(ctx)
            yield _sse_event(
                {
                    "type": "phase",
                    "phase": "phase1",
                    "message": "🤖 正在规划测试模块与边界...",
                }
            )
            try:
                _debug_log_openai_target(
                    "ai_generate_cases_stream_sdk_phase1", model_used, api_base_url
                )
                phase1_client = OpenAI(api_key=api_key, base_url=api_base_url, timeout=90.0)
                phase1 = _run_phase1_intent_analysis(
                    phase1_client,
                    model_used=model_used,
                    requirement=str(ctx.get("requirement") or ""),
                    fallback_module=str(ctx.get("module_name") or ""),
                )
                phase1_module_name = str(phase1.get("module_name") or "").strip() or str(
                    ctx.get("module_name") or ""
                )
                phase1_query = _phase1_query_text(
                    requirement=str(ctx.get("requirement") or ""),
                    phase1=phase1,
                    api_spec=str(ctx.get("api_spec") or ""),
                )
            except Exception:
                logger.exception("AI stream phase1 failed, fallback used")

            yield _sse_event(
                {
                    "type": "phase",
                    "phase": "rag",
                    "message": "📚 正在检索 AITesta 知识库规范...",
                }
            )
            phase1_block = _phase1_analysis_block(phase1)
            domain_system_with_phase1 = domain_system + "\n\n" + phase1_block
            yield _sse_event(
                {
                    "type": "phase1_analysis",
                    "data": phase1,
                }
            )
            if ctx.get("rag_enabled", True):
                rag_top_k = max(1, int(getattr(settings, "RAG_TOP_K", 5)))
                stream_system_prompt = build_rag_system_prompt(
                    domain_system_with_phase1,
                    phase1_query,
                    module_name=phase1_module_name,
                    api_spec=ctx.get("api_spec"),
                    top_k=rag_top_k,
                )
            else:
                stream_system_prompt = domain_system_with_phase1
            stream_phase2_system_prompt = stream_system_prompt + "\n\n" + _PHASE2_MULTI_CASE_MANDATE
            existing_rows: list[dict] = []
            existing_titles: list[str] = []
            try:
                from testcase.models import TestCase

                existing_qs = TestCase.objects.filter(is_deleted=False)
                if module_id:
                    existing_qs = existing_qs.filter(module_id=module_id)
                existing_rows = list(existing_qs.values("case_name"))
                existing_titles = [
                    str(x.get("case_name") or "").strip()
                    for x in existing_rows
                    if str(x.get("case_name") or "").strip()
                ]
            except Exception:
                logger.exception("读取已有用例失败（流式），跳过前置规避提示")
            stream_batch_user_prompt = build_batch_generation_prompt(
                module_name=str(ctx.get("module_name") or ""),
                requirement=str(ctx.get("requirement") or ""),
                test_type_focus=str(ctx.get("test_type_focus") or ""),
                existing_titles=existing_titles,
                min_count=max(5, AI_GENERATE_MIN_CASES),
            )
            yield _sse_event(
                {
                    "type": "phase",
                    "phase": "phase2",
                    "message": "✨ 正在结合规范生成详细用例，请稍候...",
                }
            )
            raw_parts: list[str] = []
            truncate_by_length = False
            last_ping_ts = time.monotonic()
            try:
                _debug_log_openai_target(
                    "ai_generate_cases_stream_sdk", model_used, api_base_url
                )
                client = OpenAI(
                    api_key=api_key,
                    base_url=api_base_url,
                    timeout=AI_PHASE2_TIMEOUT_SECONDS,
                )
                stream = client.chat.completions.create(
                    model=model_used,
                    messages=[
                        {"role": "system", "content": stream_phase2_system_prompt},
                        {"role": "user", "content": stream_batch_user_prompt},
                    ],
                    temperature=0.35,
                    max_tokens=AI_GENERATE_CASES_MAX_TOKENS,
                    stream=True,
                    timeout=AI_PHASE2_TIMEOUT_SECONDS,
                )
                for chunk in stream:
                    now = time.monotonic()
                    if now - last_ping_ts >= 12:
                        yield _sse_event({"type": "ping", "ts": int(now)})
                        last_ping_ts = now
                    if not chunk.choices:
                        continue
                    ch0 = chunk.choices[0]
                    fr = getattr(ch0, "finish_reason", None)
                    if fr == "length":
                        truncate_by_length = True
                    delta = ch0.delta
                    piece = (
                        getattr(delta, "content", None) if delta is not None else None
                    )
                    if piece:
                        raw_parts.append(piece)
                        yield _sse_event({"type": "delta", "text": piece})
            except AuthenticationError as e:
                logger.exception(
                    "AI stream auth failed. user_id=%s model=%s base_url=%s module_id=%s",
                    getattr(drf_request.user, "id", None),
                    model_used,
                    api_base_url,
                    module_id,
                )
                yield _sse_event(
                    {"type": "error", "message": f"API Key 无效：{e}", "detail": str(e)}
                )
                return
            except APITimeoutError:
                logger.exception(
                    "AI stream timeout. user_id=%s model=%s base_url=%s module_id=%s",
                    getattr(drf_request.user, "id", None),
                    model_used,
                    api_base_url,
                    module_id,
                )
                yield _sse_event(
                    {
                        "type": "error",
                        "message": "调用智谱接口超时，请稍后重试。",
                    }
                )
                return
            except APIConnectionError as e:
                logger.exception(
                    "AI stream upstream unreachable. user_id=%s model=%s base_url=%s module_id=%s",
                    getattr(drf_request.user, "id", None),
                    model_used,
                    api_base_url,
                    module_id,
                )
                yield _sse_event(
                    {
                        "type": "error",
                        "message": f"无法连接模型服务：{e}",
                        "detail": str(e),
                    }
                )
                return
            except APIError as e:
                logger.exception(
                    "AI stream API error. user_id=%s model=%s base_url=%s module_id=%s",
                    getattr(drf_request.user, "id", None),
                    model_used,
                    api_base_url,
                    module_id,
                )
                code = getattr(e, "status_code", None)
                msg = getattr(e, "message", None) or str(e)
                if code == 429 or "429" in str(e).lower():
                    msg = "请求过于频繁（429），请稍后再试。"
                yield _sse_event(
                    {"type": "error", "message": msg, "detail": str(e), "code": code}
                )
                return
            except Exception as e:
                logger.exception(
                    "AI stream unexpected exception. user_id=%s model=%s base_url=%s module_id=%s",
                    getattr(drf_request.user, "id", None),
                    model_used,
                    api_base_url,
                    module_id,
                )
                yield _sse_event({"type": "error", "message": str(e), "detail": str(e)})
                return

            try:
                raw = _sanitize_llm_json_text("".join(raw_parts).strip())
                if is_all_covered_output(raw):
                    yield _sse_event(
                        {
                            "type": "all_covered",
                            "phase1_analysis": phase1,
                            "message": "语义检索：当前模块下已有用例已覆盖该需求，无需生成新用例。",
                        }
                    )
                    return

                try:
                    parsed = parse_batch_json_array(raw)
                except Exception:
                    parsed = _parse_ai_cases_json(raw)
                if not parsed:
                    snippet = raw[:400] + ("…" if len(raw) > 400 else "")
                    failure_fragment = (
                        raw[-800:] if len(raw) > 800 and truncate_by_length else raw[:800]
                    )
                    if len(raw) <= 800:
                        failure_fragment = raw
                    yield _sse_event(
                        {
                            "type": "error",
                            "message": "模型返回内容无法解析为 JSON 数组。可重新生成或使用对话框中的「手动修复并导入」。",
                            "parse_failed": True,
                            "snippet": snippet,
                            "failure_fragment": failure_fragment,
                            "truncated": truncate_by_length,
                        }
                    )
                    return

                cases = []
                for i, row in enumerate(parsed):
                    norm = _normalize_generated_case(
                        normalize_batch_case_item(row, i), i, ctx.get("test_type")
                    )
                    if norm:
                        if use_api:
                            norm = enrich_normalized_case_with_api_fields(norm, row, i)
                        cases.append(norm)

                cases = _deduplicate_cases_with_guard(cases, "流式生成结果")
                existing_for_semantic = [
                    {"case_name": x.get("case_name") or "", "steps": ""}
                    for x in existing_rows
                ]
                cases = semantic_deduplicate_cases(
                    cases,
                    existing_for_semantic,
                    api_key=api_key,
                    base_url=api_base_url,
                )
                if use_api and cases:
                    renumber_api_business_ids(cases)
                retry_round = 0
                while len(cases) < AI_GENERATE_MIN_CASES and retry_round < AI_GENERATE_RETRY_ROUNDS:
                    retry_round += 1
                    yield _sse_event(
                        {
                            "type": "phase",
                            "phase": "phase2_retry",
                            "message": "✨ 首轮结果偏少，正在补充异常与边界用例...",
                        }
                    )
                    cases = _expand_cases_to_minimum_if_needed(
                        client=client,
                        model_used=model_used,
                        phase2_system_prompt=stream_phase2_system_prompt,
                        user_msg=user_msg,
                        cases=cases,
                        min_cases=AI_GENERATE_MIN_CASES,
                        test_type=ctx.get("test_type"),
                        use_api=use_api,
                    )
                cases = _enforce_cases_cap(cases, AI_GENERATE_MAX_CASES)
                if use_api and cases:
                    renumber_api_business_ids(cases)
            except Exception as parse_err:
                logger.exception("AI stream phase2 parse/normalize failed: %s", parse_err)
                yield _sse_event(
                    {
                        "type": "error",
                        "message": "大模型生成超时或格式错误",
                        "detail": str(parse_err),
                    }
                )
                return

            if not cases:
                yield _sse_event(
                    {
                        "type": "error",
                        "message": "解析后没有有效用例，请调整需求描述后重试。",
                    }
                )
                return

            yield _sse_event(
                {
                    "type": "done",
                    "success": True,
                    "phase1_analysis": phase1,
                    "message": f"已生成 {len(cases)} 条用例",
                    "cases": cases,
                    "model": model_used,
                }
            )

        response = StreamingHttpResponse(
            streaming_content=event_stream(),
            content_type="text/event-stream; charset=utf-8",
        )
        response["Cache-Control"] = "no-cache, no-store, no-transform"
        response["Pragma"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        # WSGI（如 Django dev server / wsgiref）禁止应用层设置 hop-by-hop 头（如 Connection）。
        # 是否保持连接由服务器本身决定；SSE 在 HTTP/1.1 下可正常工作，无需显式设置该头。
        return response
