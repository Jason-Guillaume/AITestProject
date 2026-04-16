import json
import logging
import importlib.util
import hashlib
import re
from difflib import SequenceMatcher
from datetime import timedelta
from pathlib import Path
import sys
import time

from django.conf import settings
from django.db.models import OuterRef, Subquery
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
    backfill_api_request_fields_in_batch,
    enrich_normalized_case_with_api_fields,
    renumber_api_business_ids,
)
from assistant.generated_case_dedup import deduplicate_generated_cases
from assistant.rag_pipeline import build_rag_system_prompt, is_all_covered_output
from assistant.knowledge_rag import KnowledgeSearcher
from assistant.ai_errors import (
    resolve_ai_generate_cases_outer_openai_error,
    resolve_ai_test_connection_openai_error,
    resolve_ai_verify_connection_openai_error,
)
from assistant.ai_prompts import (
    AI_VERIFY_CONNECTION_SYSTEM_PROMPT,
    SYSTEM_PROMPT,
    _AI_GENERATE_SYSTEM_TEMPLATE,
    _PHASE1_INTENT_SYSTEM_PROMPT,
    _PHASE1_REPAIR_SYSTEM_PROMPT,
    _PHASE2_MULTI_CASE_MANDATE,
)
from assistant.models import KnowledgeArticle, KnowledgeDocument
from assistant.permissions import (
    IsAdminOrDocumentCreator,
    user_is_knowledge_document_privileged,
)
from assistant.services.ai_governance import (
    acquire_ai_concurrency_slot,
    check_and_increment_daily_quota,
    check_and_increment_daily_quota_for_scope,
    acquire_ai_concurrency_slot_for_scope,
    release_ai_concurrency_slot,
    resolve_effective_scope_policy,
    write_ai_usage_event,
)
from assistant.serialize import KnowledgeArticleSerializer, KnowledgeDocumentSerializer
from assistant.error_parser import simplify_vector_error
from assistant.services.document_parser import (
    SUPPORTED_EXTENSIONS,
    extract_text_from_uploaded_file,
)
from testcase.models import TestModule

logger = logging.getLogger(__name__)


def _yyyymmdd_now() -> str:
    try:
        return timezone.now().strftime("%Y%m%d")
    except Exception:
        return time.strftime("%Y%m%d")


def _request_path(request) -> str:
    try:
        return str(getattr(request, "path", "") or "")[:128]
    except Exception:
        return ""


def _guard_ai_request_or_429(request, *, action: str):
    """
    AI 治理：每日配额 + 并发保护（按 user）。
    返回 (slot_acquired, denied_response_or_none)。
    """
    u = getattr(request, "user", None)
    if not u or not getattr(u, "is_authenticated", False):
        return False, None
    uid = int(getattr(u, "id", 0) or 0)
    if uid <= 0:
        return False, None

    allowed, used, limit = check_and_increment_daily_quota(
        user_id=uid, yyyymmdd=_yyyymmdd_now()
    )
    if not allowed:
        msg = f"今日 AI 调用次数已达上限（{used}/{limit}），请明日再试或联系管理员调整配额。"
        try:
            write_ai_usage_event(
                user=u,
                action=action,
                endpoint=_request_path(request),
                success=False,
                status_code=429,
                error_code="QUOTA_EXCEEDED",
                error_message=msg,
                meta={"daily_used": used, "daily_limit": limit},
            )
        except Exception:
            pass
        return False, Response(
            {"success": False, "error": msg, "message": msg, "cases": []}, status=429
        )

    # 额外：项目/组织级配额（仅在请求带 project_id / module_id / org_id 时启用）
    project_id = None
    org_id = None
    try:
        raw_pid = request.data.get("project_id")
        if raw_pid not in (None, ""):
            project_id = int(raw_pid)
    except Exception:
        project_id = None
    try:
        raw_oid = request.data.get("org_id")
        if raw_oid not in (None, ""):
            org_id = int(raw_oid)
    except Exception:
        org_id = None

    if project_id is None:
        try:
            raw_mod = request.data.get("module_id")
            mod_id = int(raw_mod) if raw_mod not in (None, "") else None
        except Exception:
            mod_id = None
        if mod_id:
            try:
                project_id = (
                    TestModule.objects.filter(pk=mod_id, is_deleted=False)
                    .values_list("project_id", flat=True)
                    .first()
                )
            except Exception:
                project_id = None

    scope_policy = None
    if project_id or org_id:
        scope_policy = resolve_effective_scope_policy(
            user_id=uid, project_id=project_id, org_id=org_id, action=action
        )
    if scope_policy and int(getattr(scope_policy, "daily_requests", 0) or 0) > 0:
        ok, s_used, s_limit = check_and_increment_daily_quota_for_scope(
            scope=getattr(scope_policy, "scope"),
            scope_id=int(getattr(scope_policy, "scope_id")),
            yyyymmdd=_yyyymmdd_now(),
            limit=int(getattr(scope_policy, "daily_requests")),
        )
        if not ok:
            msg = (
                f"当前范围（{scope_policy.scope}{scope_policy.scope_id}）"
                f"今日 AI 调用次数已达上限（{s_used}/{s_limit}），请明日再试或联系管理员调整配额。"
            )
            try:
                write_ai_usage_event(
                    user=u,
                    action=action,
                    endpoint=_request_path(request),
                    success=False,
                    status_code=429,
                    error_code="SCOPE_QUOTA_EXCEEDED",
                    error_message=msg,
                    meta={
                        "scope": scope_policy.scope,
                        "scope_id": scope_policy.scope_id,
                        "daily_used": s_used,
                        "daily_limit": s_limit,
                    },
                )
            except Exception:
                pass
            return False, Response(
                {"success": False, "error": msg, "message": msg, "cases": []},
                status=429,
            )

    acquired, cur, max_c = acquire_ai_concurrency_slot(user_id=uid)
    if not acquired:
        msg = f"当前 AI 并发过高（>{max_c}），请稍后重试。"
        try:
            write_ai_usage_event(
                user=u,
                action=action,
                endpoint=_request_path(request),
                success=False,
                status_code=429,
                error_code="CONCURRENCY_LIMIT",
                error_message=msg,
                meta={"concurrency": cur, "max_concurrency": max_c},
            )
        except Exception:
            pass
        return False, Response(
            {"success": False, "error": msg, "message": msg, "cases": []}, status=429
        )

    if scope_policy and int(getattr(scope_policy, "max_concurrency", 0) or 0) > 0:
        s_ok, s_cur, s_max = acquire_ai_concurrency_slot_for_scope(
            scope=getattr(scope_policy, "scope"),
            scope_id=int(getattr(scope_policy, "scope_id")),
            max_concurrency=int(getattr(scope_policy, "max_concurrency")),
            ttl_seconds=int(getattr(scope_policy, "concurrency_ttl_seconds", 180) or 180),
        )
        if not s_ok:
            # scope 拦截：释放 user 槽（scope 槽本次未占用成功）
            try:
                release_ai_concurrency_slot(user_id=uid)
            except Exception:
                pass
            msg = f"当前范围 AI 并发过高（>{s_max}），请稍后重试。"
            try:
                write_ai_usage_event(
                    user=u,
                    action=action,
                    endpoint=_request_path(request),
                    success=False,
                    status_code=429,
                    error_code="SCOPE_CONCURRENCY_LIMIT",
                    error_message=msg,
                    meta={
                        "scope": scope_policy.scope,
                        "scope_id": scope_policy.scope_id,
                        "concurrency": s_cur,
                        "max_concurrency": s_max,
                    },
                )
            except Exception:
                pass
            return False, Response(
                {"success": False, "error": msg, "message": msg, "cases": []},
                status=429,
            )

        # 标记 scope 槽（用于后续可选释放；即使不释放也会 TTL 到期）
        try:
            setattr(
                request,
                "_ai_scope_slot",
                {"scope": scope_policy.scope, "scope_id": scope_policy.scope_id},
            )
        except Exception:
            pass
    return True, None


def _redact_ext_config_for_run(ext_config: object) -> dict:
    """
    生成 run 记录时，对 ext_config 做轻量脱敏/瘦身：
    - 仅保留 key 列表与若干字段的长度统计，避免把大段 spec/文本落库
    """
    if not isinstance(ext_config, dict):
        return {}
    out = {"keys": [], "sizes": {}}
    try:
        keys = [str(k) for k in ext_config.keys()]
        out["keys"] = keys[:80]
        sizes = {}
        for k in keys[:80]:
            v = ext_config.get(k)
            if v is None:
                continue
            if isinstance(v, (str, bytes)):
                sizes[k] = len(v)
            elif isinstance(v, (list, dict)):
                try:
                    sizes[k] = len(v)
                except Exception:
                    pass
        out["sizes"] = sizes
    except Exception:
        return {}
    return out


def _write_ai_case_generation_run(
    *,
    user,
    action: str,
    ctx: dict,
    model_used: str,
    phase1: dict,
    phase1_override: dict | None,
    streamed: bool,
    success: bool,
    all_covered: bool,
    cases_count: int,
    latency_ms: int,
    output_chars: int,
    error_code: str = "",
    error_message: str = "",
    meta: dict | None = None,
) -> int | None:
    """
    写入 AiCaseGenerationRun，返回 run_id（失败返回 None）。
    """
    try:
        from assistant.models import AiCaseGenerationRun
    except Exception:
        return None

    requirement = str(ctx.get("requirement") or "")
    req_sha = (
        hashlib.sha256(requirement.encode("utf-8")).hexdigest() if requirement else ""
    )
    preview = re.sub(r"\s+", " ", requirement).strip()[:200] if requirement else ""
    prompt_chars = len(requirement) + len(str(ctx.get("api_spec") or ""))
    try:
        row = AiCaseGenerationRun.objects.create(
            user=user if getattr(user, "is_authenticated", False) else None,
            action=str(action or "")[:64],
            test_type=str(ctx.get("test_type") or "")[:32],
            module_id=ctx.get("module_id"),
            streamed=bool(streamed),
            model_used=str(model_used or "")[:128],
            prompt_version=str((meta or {}).get("prompt_version") or "v1")[:64],
            params=(
                _redact_ext_config_for_run(ctx.get("params") or {})
                if isinstance(ctx.get("params"), dict)
                else {}
            ),
            requirement_sha256=req_sha,
            requirement_preview=preview[:256],
            ext_config=_redact_ext_config_for_run(ctx.get("ext_config") or {}),
            phase1_analysis=phase1 if isinstance(phase1, dict) else {},
            phase1_override=(
                phase1_override if isinstance(phase1_override, dict) else {}
            ),
            success=bool(success),
            all_covered=bool(all_covered),
            cases_count=int(cases_count or 0),
            prompt_chars=int(prompt_chars or 0),
            output_chars=int(output_chars or 0),
            latency_ms=int(latency_ms or 0),
            error_code=str(error_code or "")[:64],
            error_message=str(error_message or "")[:512],
            meta=meta or {},
        )
        return int(row.id)
    except Exception:
        return None


def _knowledge_document_forbidden_if_no_object_permission(
    request, view, doc, message: str
):
    """403 with project JSON shape when any ``permission_classes`` entry denies object access."""
    for p in view.get_permissions():
        if not p.has_object_permission(request, view, doc):
            return Response({"success": False, "message": message}, status=403)
    return None


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
        "登录",
        "注册",
        "鉴权",
        "权限",
        "接口",
        "API",
        "状态码",
        "并发",
        "性能",
        "安全",
        "SQL注入",
        "越权",
        "支付",
        "订单",
        "用户",
        "搜索",
        "消息",
        "文件上传",
        "边界",
        "异常",
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
    fallback = _infer_doc_form_fallback(
        text=text, filename=filename, module_options=module_options
    )
    text = (text or "").strip()
    if not text:
        return fallback
    try:
        api_key, api_base_url, model_used = _get_active_ai_model_credentials()
    except Exception:
        return fallback
    if not api_key or not api_base_url or not model_used or not OPENAI_SDK_AVAILABLE:
        return fallback

    module_names = [
        str(x.get("name") or "").strip()
        for x in module_options
        if str(x.get("name") or "").strip()
    ]
    module_names_text = (
        "、".join(module_names[:120]) if module_names else "（无模块可选）"
    )
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
            max_size = int(
                getattr(settings, "KNOWLEDGE_UPLOAD_MAX_SIZE", 10 * 1024 * 1024)
            )
            if int(getattr(uploaded_file, "size", 0) or 0) > max_size:
                return Response(
                    {"msg": f"上传文件过大，最大支持 {max_size // 1024 // 1024}MB"},
                    status=400,
                )
            try:
                payload["markdown_content"] = extract_text_from_uploaded_file(
                    uploaded_file
                )
            except ValueError as exc:
                return Response({"msg": str(exc)}, status=400)
            except Exception:
                logger.exception(
                    "解析知识库上传文件失败: filename=%s",
                    getattr(uploaded_file, "name", ""),
                )
                return Response(
                    {"msg": "文件解析失败，请检查文件格式或内容后重试"}, status=400
                )
        elif (
            text_source == "upload"
            and not (payload.get("markdown_content") or "").strip()
        ):
            return Response({"msg": "请选择文件或填写内容"}, status=400)

        tags_val = payload.get("tags")
        if isinstance(tags_val, str):
            tags_val = tags_val.strip()
            if tags_val.startswith("["):
                try:
                    payload["tags"] = json.loads(tags_val)
                except Exception:
                    payload["tags"] = [
                        x.strip() for x in tags_val.split(",") if x.strip()
                    ]
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
                {
                    "success": False,
                    "message": f"上传文件过大，最大支持 {max_size // 1024 // 1024}MB",
                },
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
            logger.exception(
                "知识库文件预解析失败: filename=%s", getattr(uploaded_file, "name", "")
            )
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
        started_at = time.monotonic()
        slot, denied = _guard_ai_request_or_429(request, action="knowledge_autofill")
        if denied is not None:
            return denied
        uploaded_file = request.FILES.get("file")
        text = (request.data.get("text") or "").strip()
        filename = (request.data.get("filename") or "").strip()

        if uploaded_file is not None:
            filename = (uploaded_file.name or "").strip() or filename
            max_size = int(
                getattr(settings, "KNOWLEDGE_UPLOAD_MAX_SIZE", 10 * 1024 * 1024)
            )
            if int(getattr(uploaded_file, "size", 0) or 0) > max_size:
                return Response(
                    {
                        "success": False,
                        "message": f"上传文件过大，最大支持 {max_size // 1024 // 1024}MB",
                    },
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
                logger.exception(
                    "自动填充提取文本失败: filename=%s",
                    getattr(uploaded_file, "name", ""),
                )
                return Response(
                    {"success": False, "message": "文件解析失败"}, status=400
                )

        text = (text or "").strip()
        if not text:
            return Response({"success": False, "message": "缺少可分析文本"}, status=400)

        module_rows = list(
            TestModule.objects.filter(is_deleted=False).values("id", "name")[:300]
        )
        auto = _infer_doc_form_with_llm(
            text=text, filename=filename, module_options=module_rows
        )
        payload = {
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
        try:
            write_ai_usage_event(
                user=request.user,
                action="knowledge_autofill",
                endpoint=_request_path(request),
                success=True,
                status_code=200,
                latency_ms=int((time.monotonic() - started_at) * 1000),
                prompt_chars=len(text or ""),
                output_chars=len(
                    json.dumps(payload.get("data") or {}, ensure_ascii=False)
                ),
                module_id=payload["data"].get("module_id"),
                meta={"source": payload["data"].get("source")},
            )
        finally:
            if slot:
                release_ai_concurrency_slot(
                    user_id=int(getattr(request.user, "id", 0) or 0)
                )
        return Response(payload)


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

        from assistant.tasks import process_knowledge_document_task
        from assistant.services.rag_service import process_and_embed_document

        mode = _enqueue_celery_or_thread(
            celery_delay=process_knowledge_document_task.delay,
            thread_target=process_and_embed_document,
            args=(int(doc.id),),
            error_log_msg=f"知识库文档向量化失败: doc_id={doc.id}",
        )
        doc.status = KnowledgeDocument.STATUS_PROCESSING
        doc.save(update_fields=["status", "update_time"])
        enqueue_msg = (
            "文档已上传，已加入异步处理队列"
            if mode == "celery"
            else "文档已上传，正在后台处理（线程降级模式）"
        )
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
                module = TestModule.objects.filter(
                    pk=int(raw_module_id), is_deleted=False
                ).first()
            except (TypeError, ValueError):
                module = None
            if module is None:
                return Response(
                    {"success": False, "message": "module_id 无效"}, status=400
                )

        if mode not in ("upload", "url"):
            return Response(
                {"success": False, "message": "mode 仅支持 upload 或 url"}, status=400
            )

        # 2) 按模式构建文档元数据，确保文档类型、文件名、来源字段一致。
        document_type = KnowledgeDocument.DOC_TYPE_MD
        file_name = ""
        file_path = None
        final_source_url = ""
        final_title = title

        if mode == "upload":
            if uploaded_file is None:
                return Response(
                    {"success": False, "message": "upload 模式下 file 不能为空"},
                    status=400,
                )
            file_name = (getattr(uploaded_file, "name", "") or "").strip()
            if not file_name:
                return Response(
                    {"success": False, "message": "上传文件名不能为空"}, status=400
                )
            ext = file_name.lower()
            if ext.endswith(".pdf"):
                document_type = KnowledgeDocument.DOC_TYPE_PDF
            elif ext.endswith(".md"):
                document_type = KnowledgeDocument.DOC_TYPE_MD
            else:
                return Response(
                    {"success": False, "message": "仅支持 PDF 或 MD 文件"}, status=400
                )
            file_path = uploaded_file
            if not final_title:
                final_title = file_name
        else:
            if not source_url:
                return Response(
                    {"success": False, "message": "url 模式下 url 不能为空"}, status=400
                )
            if not (
                source_url.startswith("http://") or source_url.startswith("https://")
            ):
                return Response(
                    {
                        "success": False,
                        "message": "URL 必须以 http:// 或 https:// 开头",
                    },
                    status=400,
                )
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

        mode = _enqueue_celery_or_thread(
            celery_delay=process_document_rag.delay,
            thread_target=process_document_rag,
            args=(int(document.id),),
            error_log_msg=f"知识文档 RAG 处理失败: doc_id={document.id}",
        )
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
    permission_classes = [IsAuthenticated, IsAdminOrDocumentCreator]

    def get(self, request, doc_id: int):
        _mark_stuck_processing_docs_failed()
        doc = KnowledgeDocument.objects.filter(pk=doc_id, is_deleted=False).first()
        if doc is None:
            return Response({"success": False, "message": "文档不存在"}, status=404)
        denied = _knowledge_document_forbidden_if_no_object_permission(
            request, self, doc, "无权限访问该文档"
        )
        if denied is not None:
            return denied
        if doc.status == KnowledgeDocument.STATUS_COMPLETED and not (
            (doc.semantic_summary or "").strip() or (doc.semantic_chunks or [])
        ):
            summary, chunks = _build_fallback_semantic_payload(doc)
            if summary or chunks:
                doc.semantic_summary = summary
                doc.semantic_chunks = chunks
                doc.save(
                    update_fields=["semantic_summary", "semantic_chunks", "update_time"]
                )
        return Response(
            {
                "success": True,
                "data": _sanitize_doc_error_fields(
                    KnowledgeDocumentSerializer(doc).data
                ),
            }
        )


class KnowledgeDocumentChunksPreviewAPIView(APIView):
    """预览文档切片（用于监控切片质量）。"""

    permission_classes = [IsAuthenticated, IsAdminOrDocumentCreator]

    def get(self, request, doc_id: int):
        doc = KnowledgeDocument.objects.filter(pk=doc_id, is_deleted=False).first()
        if doc is None:
            return Response({"success": False, "message": "文档不存在"}, status=404)
        denied = _knowledge_document_forbidden_if_no_object_permission(
            request, self, doc, "无权限访问该文档"
        )
        if denied is not None:
            return denied

        limit = request.query_params.get("limit", 20)
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 20
        limit = min(max(limit, 1), 200)

        chunks = doc.semantic_chunks if isinstance(doc.semantic_chunks, list) else []
        summary = (doc.semantic_summary or "").strip()
        if not chunks:
            fb_summary, fb_chunks = _build_fallback_semantic_payload(doc)
            summary = summary or fb_summary
            chunks = fb_chunks if isinstance(fb_chunks, list) else []

        preview = []
        for idx, c in enumerate(chunks[:limit]):
            if isinstance(c, dict):
                text = str(c.get("text") or "").strip()
            else:
                text = str(c or "").strip()
            preview.append(
                {
                    "index": idx,
                    "text": text,
                    "chars": len(text),
                }
            )
        return Response(
            {
                "success": True,
                "data": {
                    "doc_id": doc.id,
                    "title": doc.title,
                    "status": doc.status,
                    "summary": summary,
                    "total_chunks": len(chunks),
                    "preview_chunks": preview,
                },
            }
        )


class KnowledgeArticleChunksPreviewAPIView(APIView):
    """预览知识文章切片（用于监控切片质量）。"""

    permission_classes = [IsAuthenticated]

    def get(self, request, article_id: int):
        article = KnowledgeArticle.objects.filter(
            pk=article_id, is_deleted=False
        ).first()
        if article is None:
            return Response({"success": False, "message": "文章不存在"}, status=404)

        limit = request.query_params.get("limit", 20)
        try:
            limit = int(limit)
        except (TypeError, ValueError):
            limit = 20
        limit = min(max(limit, 1), 200)

        from assistant.knowledge_rag import _build_article_text, _chunk_text

        text = _build_article_text(article)
        chunks = _chunk_text(text)
        preview = [
            {"index": i, "text": (c or ""), "chars": len(c or "")}
            for i, c in enumerate(chunks[:limit])
        ]
        return Response(
            {
                "success": True,
                "data": {
                    "article_id": article.id,
                    "title": article.title,
                    "category": article.category,
                    "total_chunks": len(chunks),
                    "preview_chunks": preview,
                },
            }
        )


class KnowledgeDocumentRetryAPIView(APIView):
    permission_classes = [IsAuthenticated, IsAdminOrDocumentCreator]

    def post(self, request, doc_id: int):
        doc = KnowledgeDocument.objects.filter(pk=doc_id, is_deleted=False).first()
        if doc is None:
            return Response({"success": False, "message": "文档不存在"}, status=404)
        denied = _knowledge_document_forbidden_if_no_object_permission(
            request, self, doc, "无权限重试该任务"
        )
        if denied is not None:
            return denied
        # 允许待处理/失败/已完成状态重提任务；仅“处理中”禁止重复触发。
        if doc.status == KnowledgeDocument.STATUS_PROCESSING:
            return Response(
                {"success": False, "message": "当前任务仍在处理中，无需重试"},
                status=400,
            )

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
    permission_classes = [IsAuthenticated, IsAdminOrDocumentCreator]

    def delete(self, request, doc_id: int):
        doc = KnowledgeDocument.objects.filter(pk=doc_id, is_deleted=False).first()
        if doc is None:
            return Response({"success": False, "message": "文档不存在"}, status=404)
        denied = _knowledge_document_forbidden_if_no_object_permission(
            request, self, doc, "无权限删除该文档"
        )
        if denied is not None:
            return denied

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
        if not user_is_knowledge_document_privileged(request.user):
            qs = qs.filter(creator=request.user)
        rows = qs.order_by("-created_at")[:page_size]
        return Response(
            {
                "success": True,
                "results": _sanitize_doc_error_fields(
                    KnowledgeDocumentSerializer(rows, many=True).data
                ),
            }
        )


class KnowledgeRuntimeStatusAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _mark_stuck_processing_docs_failed()
        celery_installed = importlib.util.find_spec("celery") is not None
        queue_mode = "celery" if celery_installed else "thread_fallback"
        base_qs = KnowledgeDocument.objects.filter(is_deleted=False)
        if not user_is_knowledge_document_privileged(request.user):
            base_qs = base_qs.filter(creator=request.user)
        counters = {
            "pending": base_qs.filter(status=KnowledgeDocument.STATUS_PENDING).count(),
            "processing": base_qs.filter(
                status=KnowledgeDocument.STATUS_PROCESSING
            ).count(),
            "completed": base_qs.filter(
                status=KnowledgeDocument.STATUS_COMPLETED
            ).count(),
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
IFLYTEK_MAAS_OPENAI_BASE = "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2"
IFLYTEK_MAAS_CHAT_COMPLETIONS = (
    "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2/chat/completions"
)
IFLYTEK_MAAS_MODEL_TYPE = "iflytek-spark-maas-coding"


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


def _is_iflytek_maas_model(model: str) -> bool:
    m = (model or "").strip().lower()
    if not m:
        return False
    return (
        m == IFLYTEK_MAAS_MODEL_TYPE or "iflytek" in m or "spark" in m or "astron" in m
    )


def _resolve_openai_target(model: str, base_url: str):
    """
    统一解析 OpenAI 兼容目标：
    - 不再覆盖模型名：前端/配置传什么模型，就按什么模型请求
    - 若模型看起来是讯飞系且未填 base_url，则补默认 /v2 根路径
    """
    m = (model or "").strip()
    b = (base_url or "").strip()
    if _is_iflytek_maas_model(m) and not b:
        b = IFLYTEK_MAAS_OPENAI_BASE
    return m, b


def _normalize_openai_sdk_base_url(base_url: str, model: str) -> str:
    """
    OpenAI Python SDK 期望 base_url 是“根路径”（如 .../v2），
    若传入了 .../chat/completions 会导致 SDK 再拼一次路径而 404。
    """
    raw = (base_url or "").strip().rstrip("/")
    if not raw:
        return raw
    if raw.endswith("/chat/completions"):
        raw = raw[: -len("/chat/completions")]
    # 讯飞模型兜底：若被裁成空或异常，回退到标准 /v2 根路径
    if _is_iflytek_maas_model(model) and not raw:
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

        # 与 AiTestConnectionAPIView 统一：使用 OpenAI SDK 调用兼容端点
        if not OPENAI_SDK_AVAILABLE:
            return Response(
                {"code": 400, "msg": _openai_missing_response_json(), "data": None},
                status=200,
            )

        api_base_url = _normalize_openai_sdk_base_url(base_url, model).rstrip("/")
        if not api_base_url:
            return Response(
                {
                    "code": 400,
                    "msg": "当前模型需填写自定义 API 地址（Base URL）",
                    "data": None,
                },
                status=200,
            )

        try:
            _debug_log_openai_target("llm_test_connection_sdk", model, api_base_url)
            client = OpenAI(api_key=api_key, base_url=api_base_url, timeout=20.0)
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": "Connection test. Reply as instructed.",
                    },
                ],
                max_tokens=80,
                temperature=0.3,
            )
            choice = completion.choices[0].message
            reply = (getattr(choice, "content", None) or "").strip()
        except Exception as e:

            def _err_body(msg: str, status_code: int = 400):
                return Response({"code": 400, "msg": msg, "data": None}, status=200)

            handled = resolve_ai_test_connection_openai_error(
                e,
                request=request,
                model=model,
                api_base_url=api_base_url,
                err_body=_err_body,
            )
            if handled is not None:
                return handled
            return Response(
                {"code": 400, "msg": f"请求异常: {str(e)}", "data": None},
                status=200,
            )

        if not reply:
            return Response(
                {
                    "code": 400,
                    "msg": "模型未返回有效内容，请检查 model 名称与账户权限。",
                    "data": None,
                },
                status=200,
            )

        return Response(
            {"code": 200, "msg": "连接成功", "data": {"reply": reply, "model": model}},
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
        started_at = time.monotonic()
        slot, denied = _guard_ai_request_or_429(request, action="test_connection")
        if denied is not None:
            return denied
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
        except Exception as e:
            handled = resolve_ai_test_connection_openai_error(
                e,
                request=request,
                model=model,
                api_base_url=api_base_url,
                err_body=err_body,
            )
            if handled is not None:
                try:
                    write_ai_usage_event(
                        user=request.user,
                        action="test_connection",
                        endpoint=_request_path(request),
                        success=False,
                        status_code=int(getattr(handled, "status_code", 400) or 400),
                        model_used=model,
                        latency_ms=int((time.monotonic() - started_at) * 1000),
                        error_code="UPSTREAM_ERROR",
                        error_message=str(e),
                    )
                finally:
                    if slot:
                        release_ai_concurrency_slot(
                            user_id=int(getattr(request.user, "id", 0) or 0)
                        )
                return handled
            logger.exception(
                "AI test connection unexpected exception. user_id=%s model=%s base_url=%s",
                getattr(request.user, "id", None),
                model,
                api_base_url,
            )
            resp = err_body(str(e), status_code=500)
            try:
                write_ai_usage_event(
                    user=request.user,
                    action="test_connection",
                    endpoint=_request_path(request),
                    success=False,
                    status_code=500,
                    model_used=model,
                    latency_ms=int((time.monotonic() - started_at) * 1000),
                    error_code="UNEXPECTED_ERROR",
                    error_message=str(e),
                )
            finally:
                if slot:
                    release_ai_concurrency_slot(
                        user_id=int(getattr(request.user, "id", 0) or 0)
                    )
            return resp

        if not reply:
            resp = err_body("模型未返回有效内容，请检查 model 名称与账户权限。")
            try:
                write_ai_usage_event(
                    user=request.user,
                    action="test_connection",
                    endpoint=_request_path(request),
                    success=False,
                    status_code=int(getattr(resp, "status_code", 400) or 400),
                    model_used=model,
                    latency_ms=int((time.monotonic() - started_at) * 1000),
                    error_code="EMPTY_REPLY",
                    error_message="模型未返回有效内容",
                )
            finally:
                if slot:
                    release_ai_concurrency_slot(
                        user_id=int(getattr(request.user, "id", 0) or 0)
                    )
            return resp

        resp = Response(
            {
                "success": True,
                "message": "连接成功",
                "error": None,
                "reply": reply,
                "model": model,
            },
            status=200,
        )
        try:
            write_ai_usage_event(
                user=request.user,
                action="test_connection",
                endpoint=_request_path(request),
                success=True,
                status_code=200,
                model_used=model,
                latency_ms=int((time.monotonic() - started_at) * 1000),
                output_chars=len(reply or ""),
            )
        finally:
            if slot:
                release_ai_concurrency_slot(
                    user_id=int(getattr(request.user, "id", 0) or 0)
                )
        return resp


class AiVerifyConnectionAPIView(APIView):
    """
    POST /api/ai/verify-connection/
    专用连通性校验：仅依赖 api_key，固定智谱 v4 base_url 与 glm-4.7-flash。
    """

    permission_classes = [IsAuthenticated]

    _VERIFY_MODEL = "glm-4.7-flash"
    _VERIFY_BASE = "https://open.bigmodel.cn/api/paas/v4"

    def post(self, request):
        started_at = time.monotonic()
        slot, denied = _guard_ai_request_or_429(request, action="verify_connection")
        if denied is not None:
            return denied
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
                    {"role": "system", "content": AI_VERIFY_CONNECTION_SYSTEM_PROMPT},
                    {"role": "user", "content": "测试连通性。"},
                ],
                max_tokens=60,
                temperature=0.1,
            )
            choice = completion.choices[0].message
            reply = (getattr(choice, "content", None) or "").strip()
        except Exception as e:
            handled = resolve_ai_verify_connection_openai_error(
                e,
                request=request,
                model=model,
                base_url=base_url,
                fail=fail,
            )
            if handled is not None:
                try:
                    write_ai_usage_event(
                        user=request.user,
                        action="verify_connection",
                        endpoint=_request_path(request),
                        success=False,
                        status_code=int(getattr(handled, "status_code", 400) or 400),
                        model_used=model,
                        latency_ms=int((time.monotonic() - started_at) * 1000),
                        error_code="UPSTREAM_ERROR",
                        error_message=str(e),
                    )
                finally:
                    if slot:
                        release_ai_concurrency_slot(
                            user_id=int(getattr(request.user, "id", 0) or 0)
                        )
                return handled
            logger.exception(
                "AI verify connection unexpected exception. user_id=%s model=%s base_url=%s",
                getattr(request.user, "id", None),
                model,
                base_url,
            )
            resp = fail(str(e), status_code=500)
            try:
                write_ai_usage_event(
                    user=request.user,
                    action="verify_connection",
                    endpoint=_request_path(request),
                    success=False,
                    status_code=500,
                    model_used=model,
                    latency_ms=int((time.monotonic() - started_at) * 1000),
                    error_code="UNEXPECTED_ERROR",
                    error_message=str(e),
                )
            finally:
                if slot:
                    release_ai_concurrency_slot(
                        user_id=int(getattr(request.user, "id", 0) or 0)
                    )
            return resp

        if not reply:
            resp = fail("模型未返回内容，请检查账号是否开通该模型。")
            try:
                write_ai_usage_event(
                    user=request.user,
                    action="verify_connection",
                    endpoint=_request_path(request),
                    success=False,
                    status_code=int(getattr(resp, "status_code", 400) or 400),
                    model_used=model,
                    latency_ms=int((time.monotonic() - started_at) * 1000),
                    error_code="EMPTY_REPLY",
                    error_message="模型未返回内容",
                )
            finally:
                if slot:
                    release_ai_concurrency_slot(
                        user_id=int(getattr(request.user, "id", 0) or 0)
                    )
            return resp

        resp = Response(
            {
                "success": True,
                "message": "连接成功",
                "error": None,
                "reply": reply,
                "model": model,
            },
            status=200,
        )
        try:
            write_ai_usage_event(
                user=request.user,
                action="verify_connection",
                endpoint=_request_path(request),
                success=True,
                status_code=200,
                model_used=model,
                latency_ms=int((time.monotonic() - started_at) * 1000),
                output_chars=len(reply or ""),
            )
        finally:
            if slot:
                release_ai_concurrency_slot(
                    user_id=int(getattr(request.user, "id", 0) or 0)
                )
        return resp


AI_GENERATE_MODEL = "glm-4.7-flash"
AI_GENERATE_CASES_MAX_TOKENS = max(
    4096, int(getattr(settings, "AI_GENERATE_CASES_MAX_TOKENS", 8192))
)
AI_GENERATE_MIN_CASES = max(1, int(getattr(settings, "AI_GENERATE_MIN_CASES", 4)))
AI_GENERATE_MAX_CASES = max(
    AI_GENERATE_MIN_CASES, int(getattr(settings, "AI_GENERATE_MAX_CASES", 20))
)
AI_GENERATE_RETRY_ROUNDS = max(0, int(getattr(settings, "AI_GENERATE_RETRY_ROUNDS", 2)))
AI_PHASE2_TIMEOUT_SECONDS = float(getattr(settings, "AI_PHASE2_TIMEOUT_SECONDS", 60.0))
AI_GENERATE_TOTAL_TIMEOUT_SECONDS = float(
    getattr(settings, "AI_GENERATE_TOTAL_TIMEOUT_SECONDS", 70.0)
)


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
    dedup_debug = _parse_bool_flag(
        request.data.get("dedup_debug") or request.data.get("debug_dedup")
    )

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
            "dedup_debug": dedup_debug,
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


def _build_ai_generate_system_prompt(
    module_name: str,
    requirement: str,
    test_type_focus: str | None = None,
) -> str:
    """Fill module and requirement into the expert system template."""
    mn = (
        module_name or ""
    ).strip() or "（未指定模块，请仅围绕需求归纳；module_name 须为简体中文）"
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


def _run_phase1_intent_analysis(
    client, model_used: str, requirement: str, fallback_module: str = ""
) -> dict:
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
                parsed["module_name"] = (
                    fallback_module or ""
                ).strip() or "通用功能模块"
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
                parsed2["module_name"] = (
                    fallback_module or ""
                ).strip() or "通用功能模块"
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
        q += "\n\n【接口定义原文摘录】\n" + (
            spec[:6000] + ("...(truncated)" if len(spec) > 6000 else "")
        )
    return q.strip()


def _is_placeholder_module_name(name: str) -> bool:
    t = (name or "").strip()
    if not t:
        return True
    return "未指定模块" in t or "module_name" in t


def _backfill_case_module_names(cases: list[dict], *name_candidates: str) -> None:
    """
    批量生成 JSON 模板历史上未透传 module_name；模型若漏填，用当前匹配模块 / Phase1 推导名补全，
    避免预览「目标模块」全空且导入强依赖「默认模块」。
    """
    fb = ""
    for cand in name_candidates:
        t = str(cand or "").strip()
        if t and not _is_placeholder_module_name(t):
            fb = t
            break
    if not fb:
        return
    for row in cases:
        if not isinstance(row, dict):
            continue
        if str(row.get("module_name") or "").strip():
            continue
        row["module_name"] = fb


def _module_name_key(name: str) -> str:
    t = (name or "").strip().lower()
    if not t:
        return ""
    return re.sub(r"[\s\-_，,。.:：/\\]+", "", t)


def _resolve_effective_module(
    module_id, ctx_module_name: str, phase1_module_name: str, test_type: str
):
    """
    未指定 module_id 时，尝试按 phase1 推导模块名自动匹配 TestModule。
    返回：(effective_module_id, effective_module_name)
    """
    if module_id:
        return module_id, (ctx_module_name or "").strip()

    target = (phase1_module_name or "").strip() or (ctx_module_name or "").strip()
    if _is_placeholder_module_name(target):
        return (
            None,
            (phase1_module_name or "").strip() or (ctx_module_name or "").strip(),
        )

    try:
        qs = TestModule.objects.filter(is_deleted=False)
        tt = (test_type or "").strip()
        if tt:
            qs = qs.filter(test_type=tt)
        module_rows = list(qs.values("id", "name")[:1000])
    except Exception:
        logger.exception("自动匹配模块失败：读取模块列表异常")
        return None, target

    if not module_rows:
        return None, target

    target_key = _module_name_key(target)
    # 1) 精确（归一化后）匹配
    for row in module_rows:
        name = str(row.get("name") or "").strip()
        if _module_name_key(name) == target_key:
            return int(row.get("id")), name
    # 2) 包含匹配
    for row in module_rows:
        name = str(row.get("name") or "").strip()
        name_key = _module_name_key(name)
        if (
            target_key
            and name_key
            and (target_key in name_key or name_key in target_key)
        ):
            return int(row.get("id")), name
    # 3) 相似度匹配
    best = None
    best_score = 0.0
    for row in module_rows:
        name = str(row.get("name") or "").strip()
        score = SequenceMatcher(None, target_key, _module_name_key(name)).ratio()
        if score > best_score:
            best = row
            best_score = score
    if best and best_score >= 0.58:
        return int(best.get("id")), str(best.get("name") or "").strip()
    return None, target


def _load_existing_case_context(module_id, test_type: str):
    """
    读取去重上下文：
    - existing_rows: 含 case_name 与 steps（首步骤+期望），用于语义去重
    - existing_titles: 用于标题硬去重提示
    """
    from testcase.models import TestCase, TestCaseStep

    existing_qs = TestCase.objects.filter(is_deleted=False)
    tt = (test_type or "").strip()
    if tt:
        existing_qs = existing_qs.filter(test_type=tt)
    if module_id:
        existing_qs = existing_qs.filter(module_id=module_id)
    first_step_desc_sq = Subquery(
        TestCaseStep.objects.filter(testcase_id=OuterRef("id"), is_deleted=False)
        .order_by("step_number", "id")
        .values("step_desc")[:1]
    )
    first_expected_sq = Subquery(
        TestCaseStep.objects.filter(testcase_id=OuterRef("id"), is_deleted=False)
        .order_by("step_number", "id")
        .values("expected_result")[:1]
    )
    case_rows = list(
        existing_qs.annotate(
            _first_step_desc=first_step_desc_sq,
            _first_expected=first_expected_sq,
        ).values("case_name", "_first_step_desc", "_first_expected")[:3000]
    )
    existing_rows = []
    for x in case_rows:
        step_desc = str(x.get("_first_step_desc") or "").strip()
        expected = str(x.get("_first_expected") or "").strip()
        steps = f"{step_desc}\n{expected}".strip() if (step_desc or expected) else ""
        existing_rows.append(
            {"case_name": str(x.get("case_name") or "").strip(), "steps": steps}
        )
    existing_titles = [x["case_name"] for x in existing_rows if x.get("case_name")]
    return existing_rows, existing_titles


def _enqueue_celery_or_thread(
    *, celery_delay, thread_target, args: tuple, error_log_msg: str
):
    """
    优先使用 Celery delay；不可用时降级线程执行。
    返回: "celery" | "thread"
    """
    try:
        celery_delay(*args)
        return "celery"
    except Exception:
        import threading

        def _wrapped():
            try:
                thread_target(*args)
            except Exception:
                logger.exception(error_log_msg)

        threading.Thread(target=_wrapped, daemon=True).start()
        return "thread"


def _normalize_case_name_for_exact_dedup(name: str) -> str:
    t = (name or "").strip().lower()
    if not t:
        return ""
    return re.sub(r"[\W_]+", "", t)


def _drop_cases_duplicated_with_existing_titles(
    cases: list[dict], existing_titles: list[str]
) -> list[dict]:
    if not cases or not existing_titles:
        return cases
    existing_keys = {
        _normalize_case_name_for_exact_dedup(x) for x in existing_titles if x
    }
    out = []
    for row in cases:
        key = _normalize_case_name_for_exact_dedup(str(row.get("case_name") or ""))
        if key and key in existing_keys:
            continue
        out.append(row)
    return out


def _parse_bool_flag(v) -> bool:
    if isinstance(v, bool):
        return v
    t = str(v or "").strip().lower()
    return t in {"1", "true", "yes", "y", "on"}


def _collect_case_names(cases: list[dict]) -> list[str]:
    out = []
    for row in cases or []:
        name = str((row or {}).get("case_name") or "").strip()
        if name:
            out.append(name)
    return out


def _diff_dropped_names(
    before_names: list[str], after_names: list[str], limit: int = 20
) -> list[str]:
    after_set = set(after_names)
    dropped = []
    for n in before_names:
        if n not in after_set:
            dropped.append(n)
    # 去重并保序
    uniq = []
    seen = set()
    for n in dropped:
        if n in seen:
            continue
        seen.add(n)
        uniq.append(n)
    return uniq[: max(1, int(limit))]


def _apply_dedup_pipeline(
    *,
    cases: list[dict],
    existing_titles: list[str],
    existing_rows: list[dict],
    api_key: str,
    base_url: str,
    debug: bool = False,
    mode: str = "drop",
):
    before_names = _collect_case_names(cases)
    mode = (mode or "drop").strip().lower()
    after_exact = (
        _drop_cases_duplicated_with_existing_titles(cases, existing_titles)
        if mode == "drop"
        else list(cases or [])
    )
    after_exact_names = _collect_case_names(after_exact)
    after_semantic = (
        semantic_deduplicate_cases(
            after_exact,
            existing_rows,
            api_key=api_key,
            base_url=base_url,
        )
        if mode == "drop"
        else list(after_exact or [])
    )
    after_semantic_names = _collect_case_names(after_semantic)
    highlight = mode == "highlight"
    candidates = None
    if highlight and after_semantic and existing_rows:
        try:
            from assistant.generated_case_dedup import string_similarity_candidates
            from assistant.services.semantic_dedup import semantic_similarity_candidates

            str_cands = string_similarity_candidates(
                after_semantic, existing_rows, top_k=3
            )
            sem_cands = semantic_similarity_candidates(
                after_semantic,
                existing_rows,
                api_key=api_key,
                base_url=base_url,
                top_k=3,
            )
            candidates = {"string": str_cands, "semantic": sem_cands}
        except Exception:
            logger.exception("相似候选计算失败，已跳过")

    if not debug and not highlight:
        return after_semantic, None
    report = {
        "input_count": len(cases),
        "after_exact_title_dedup_count": len(after_exact),
        "after_semantic_dedup_count": len(after_semantic),
        "dropped_by_exact_title_dedup": _diff_dropped_names(
            before_names, after_exact_names
        ),
        "dropped_by_semantic_dedup": _diff_dropped_names(
            after_exact_names, after_semantic_names
        ),
    }
    if highlight:
        report["similar_candidates"] = candidates
    return after_semantic, report


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
    steps_list = item.get("steps_list") or item.get("stepsList")
    if steps_list is None and isinstance(item.get("steps"), list):
        steps_list = item.get("steps")
    if isinstance(steps_list, list):
        norm_steps_list = []
        for it in steps_list:
            if not isinstance(it, dict):
                continue
            desc = str(
                it.get("step_desc") or it.get("desc") or it.get("action") or ""
            ).strip()
            if not desc:
                continue
            exp2 = str(it.get("expected_result") or it.get("expected") or "").strip()
            norm_steps_list.append(
                {"step_desc": desc[:4000], "expected_result": exp2[:2000]}
            )
        steps_list = norm_steps_list
        if not steps and norm_steps_list:
            steps = "\n".join(
                f"{i+1}. {x['step_desc']}" for i, x in enumerate(norm_steps_list)
            )
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
        "steps_list": steps_list if isinstance(steps_list, list) else None,
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
    brief_names = [
        str(x.get("case_name") or "").strip() for x in cases[:20] if isinstance(x, dict)
    ]
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
        raw = _sanitize_llm_json_text(
            (completion.choices[0].message.content or "").strip()
        )
        parsed = _parse_ai_cases_json(raw)
        if not parsed:
            return cases
        extra_cases = []
        for i, row in enumerate(parsed):
            norm = _normalize_generated_case(row, len(cases) + i, test_type)
            if norm:
                if use_api:
                    norm = enrich_normalized_case_with_api_fields(
                        norm, row, len(cases) + i
                    )
                extra_cases.append(norm)
        if not extra_cases:
            return cases
        merged = cases + extra_cases
        merged = _deduplicate_cases_with_guard(merged, "补生成结果")
        if use_api and merged:
            renumber_api_business_ids(merged)
            backfill_api_request_fields_in_batch(merged)
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

    @staticmethod
    def _fail(msg: str, *, status_code=400, code: str = "BAD_REQUEST"):
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

    @staticmethod
    def _timeout_guard(started_at: float):
        elapsed = time.monotonic() - started_at
        if elapsed > AI_GENERATE_TOTAL_TIMEOUT_SECONDS:
            return AiGenerateCasesAPIView._fail(
                "大模型生成超时或格式错误",
                status_code=500,
                code="GENERATION_TIMEOUT",
            )
        return None

    @staticmethod
    def _run_phase2_parse(
        client, *, model_used: str, phase2_system_prompt: str, batch_user_prompt: str
    ):
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
            raw = _sanitize_llm_json_text(
                (completion.choices[0].message.content or "").strip()
            )
            try:
                parsed = parse_batch_json_array(raw)
            except Exception:
                parsed = _parse_ai_cases_json(raw)
            return raw, parsed
        except Exception:
            raise

    def post(self, request):
        started_at = time.monotonic()
        slot, denied = _guard_ai_request_or_429(request, action="generate_cases")
        if denied is not None:
            return denied

        ctx, err = _prepare_ai_generate_context(request)
        if err:
            resp = self._fail(err, status_code=400, code="INVALID_INPUT")
            try:
                write_ai_usage_event(
                    user=request.user,
                    action="generate_cases",
                    endpoint=_request_path(request),
                    success=False,
                    status_code=400,
                    streamed=False,
                    latency_ms=int((time.monotonic() - started_at) * 1000),
                    error_code="INVALID_INPUT",
                    error_message=err,
                )
            finally:
                if slot:
                    release_ai_concurrency_slot(
                        user_id=int(getattr(request.user, "id", 0) or 0)
                    )
            return resp

        if not OPENAI_SDK_AVAILABLE:
            resp = self._fail(
                _openai_missing_response_json(),
                status_code=503,
                code="SDK_NOT_AVAILABLE",
            )
            try:
                write_ai_usage_event(
                    user=request.user,
                    action="generate_cases",
                    endpoint=_request_path(request),
                    success=False,
                    status_code=503,
                    streamed=False,
                    latency_ms=int((time.monotonic() - started_at) * 1000),
                    error_code="SDK_NOT_AVAILABLE",
                    error_message="OpenAI SDK 不可用",
                )
            finally:
                if slot:
                    release_ai_concurrency_slot(
                        user_id=int(getattr(request.user, "id", 0) or 0)
                    )
            return resp

        guard_result = self._timeout_guard(started_at)
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
        dedup_debug_report = None

        try:
            _debug_log_openai_target(
                "ai_generate_cases_sync_sdk", model_used, api_base_url
            )
            client = OpenAI(api_key=api_key, base_url=api_base_url, timeout=120.0)
            phase1_override = (
                request.data.get("phase1_override")
                if isinstance(request.data, dict)
                else None
            )
            if isinstance(phase1_override, dict):
                phase1 = phase1_override
            else:
                phase1 = _run_phase1_intent_analysis(
                    client,
                    model_used=model_used,
                    requirement=str(ctx.get("requirement") or ""),
                    fallback_module=str(ctx.get("module_name") or ""),
                )
            phase1_module = str(phase1.get("module_name") or "").strip() or str(
                ctx.get("module_name") or ""
            )
            phase1_require = _phase1_query_text(
                requirement=str(ctx.get("requirement") or ""),
                phase1=phase1,
                api_spec=str(ctx.get("api_spec") or ""),
            )
            phase1_block = _phase1_analysis_block(phase1)
            domain_system_with_phase1 = domain_system + "\n\n" + phase1_block
            guard_result = self._timeout_guard(started_at)
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

            # 未选模块时：用 Phase1 推导模块名自动匹配 module_id，确保 RAG/去重作用在正确范围
            effective_module_id, effective_module_name = _resolve_effective_module(
                module_id=module_id,
                ctx_module_name=str(ctx.get("module_name") or ""),
                phase1_module_name=phase1_module,
                test_type=str(ctx.get("test_type") or ""),
            )

            # 生成前规避：读取模块已有标题，注入批量生成 Prompt，降低意图重复概率
            existing_rows: list[dict] = []
            existing_titles: list[str] = []
            try:
                existing_rows, existing_titles = _load_existing_case_context(
                    module_id=effective_module_id,
                    test_type=str(ctx.get("test_type") or ""),
                )
            except Exception:
                logger.exception("读取已有用例失败，跳过前置规避提示")

            batch_user_prompt = build_batch_generation_prompt(
                module_name=effective_module_name
                or phase1_module
                or str(ctx.get("module_name") or ""),
                requirement=str(ctx.get("requirement") or ""),
                test_type_focus=str(ctx.get("test_type_focus") or ""),
                existing_titles=existing_titles,
                min_count=max(5, AI_GENERATE_MIN_CASES),
            )
            try:
                raw, parsed = self._run_phase2_parse(
                    client,
                    model_used=model_used,
                    phase2_system_prompt=phase2_system_prompt,
                    batch_user_prompt=batch_user_prompt,
                )
                if not parsed:
                    snippet = raw[:400] + ("…" if len(raw) > 400 else "")
                    return self._fail(
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
                dedup_mode = str(
                    ctx.get("dedup_mode") or request.data.get("dedup_mode") or "drop"
                )
                cases, dedup_debug_report = _apply_dedup_pipeline(
                    cases=cases,
                    existing_titles=existing_titles,
                    existing_rows=existing_rows,
                    api_key=api_key,
                    base_url=api_base_url,
                    debug=bool(ctx.get("dedup_debug")),
                    mode=dedup_mode,
                )
                retry_round = 0
                while (
                    len(cases) < AI_GENERATE_MIN_CASES
                    and retry_round < AI_GENERATE_RETRY_ROUNDS
                ):
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
                _backfill_case_module_names(
                    cases,
                    effective_module_name,
                    phase1_module,
                    str(ctx.get("module_name") or ""),
                )
                if use_api and cases:
                    backfill_api_request_fields_in_batch(cases)

                if not cases:
                    return self._fail(
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
                return self._fail(
                    "大模型生成超时或格式错误", status_code=500, code="PHASE2_TIMEOUT"
                )
            except Exception as phase2_error:
                logger.exception(
                    "AI generate cases phase2 failed. user_id=%s model=%s base_url=%s module_id=%s err=%s",
                    getattr(request.user, "id", None),
                    model_used,
                    api_base_url,
                    module_id,
                    phase2_error,
                )
                return self._fail(
                    "大模型生成超时或格式错误", status_code=500, code="PHASE2_FAILED"
                )
        except Exception as e:
            handled = resolve_ai_generate_cases_outer_openai_error(
                e,
                request=request,
                model_used=model_used,
                api_base_url=api_base_url,
                module_id=module_id,
                fail=self._fail,
            )
            if handled is not None:
                return handled
            logger.exception(
                "AI generate cases unexpected exception. user_id=%s model=%s base_url=%s module_id=%s",
                getattr(request.user, "id", None),
                model_used,
                api_base_url,
                module_id,
            )
            return self._fail(str(e), status_code=500, code="UNEXPECTED_ERROR")

        if is_all_covered_output(raw):
            run_id = _write_ai_case_generation_run(
                user=request.user,
                action="generate_cases",
                ctx=ctx,
                model_used=model_used,
                phase1=phase1,
                phase1_override=(
                    request.data.get("phase1_override")
                    if isinstance(request.data, dict)
                    else None
                ),
                streamed=False,
                success=True,
                all_covered=True,
                cases_count=0,
                latency_ms=int((time.monotonic() - started_at) * 1000),
                output_chars=0,
                meta={
                    "dedup_debug": bool(ctx.get("dedup_debug")),
                    "prompt_version": "v1",
                },
            )
            resp = Response(
                {
                    "success": True,
                    "all_covered": True,
                    "phase1_analysis": phase1,
                    "run_id": run_id,
                    "error": None,
                    "cases": [],
                    "message": "语义检索：当前模块下已有用例已覆盖该需求，无需生成新用例。",
                    "model": model_used,
                },
                status=200,
            )
            try:
                write_ai_usage_event(
                    user=request.user,
                    action="generate_cases",
                    endpoint=_request_path(request),
                    success=True,
                    status_code=200,
                    model_used=model_used,
                    test_type=str(ctx.get("test_type") or ""),
                    module_id=ctx.get("module_id"),
                    streamed=False,
                    all_covered=True,
                    latency_ms=int((time.monotonic() - started_at) * 1000),
                    prompt_chars=len(str(ctx.get("requirement") or ""))
                    + len(str(ctx.get("api_spec") or "")),
                    output_chars=0,
                    cases_count=0,
                    meta={
                        "dedup_debug": bool(ctx.get("dedup_debug")),
                        "run_id": run_id,
                        "prompt_version": "v1",
                    },
                )
            finally:
                if slot:
                    release_ai_concurrency_slot(
                        user_id=int(getattr(request.user, "id", 0) or 0)
                    )
            return resp

        guard_result = self._timeout_guard(started_at)
        if guard_result is not None:
            return guard_result

        resp_payload = {
            "success": True,
            "phase1_analysis": phase1,
            "error": None,
            "message": f"已生成 {len(cases)} 条用例",
            "cases": cases,
            "model": model_used,
        }
        run_id = _write_ai_case_generation_run(
            user=request.user,
            action="generate_cases",
            ctx=ctx,
            model_used=model_used,
            phase1=phase1,
            phase1_override=(
                request.data.get("phase1_override")
                if isinstance(request.data, dict)
                else None
            ),
            streamed=False,
            success=True,
            all_covered=False,
            cases_count=len(cases),
            latency_ms=int((time.monotonic() - started_at) * 1000),
            output_chars=len(
                json.dumps(resp_payload.get("cases") or [], ensure_ascii=False)
            ),
            meta={"dedup_debug": bool(ctx.get("dedup_debug")), "prompt_version": "v1"},
        )
        resp_payload["run_id"] = run_id
        if ctx.get("dedup_debug"):
            resp_payload["dedup_debug"] = dedup_debug_report
        elif isinstance(dedup_debug_report, dict) and dedup_debug_report.get(
            "similar_candidates"
        ):
            # highlight 模式：把相似候选直接回传给前端展示（不做过滤）
            sim = dedup_debug_report.get("similar_candidates") or {}
            str_cands = sim.get("string") if isinstance(sim, dict) else None
            sem_cands = sim.get("semantic") if isinstance(sim, dict) else None
            for i, row in enumerate(resp_payload["cases"]):
                if not isinstance(row, dict):
                    continue
                row["similar_candidates"] = {
                    "string": (
                        str_cands[i]
                        if isinstance(str_cands, list) and i < len(str_cands)
                        else []
                    ),
                    "semantic": (
                        sem_cands[i]
                        if isinstance(sem_cands, list) and i < len(sem_cands)
                        else []
                    ),
                }
        resp = Response(resp_payload, status=200)
        try:
            write_ai_usage_event(
                user=request.user,
                action="generate_cases",
                endpoint=_request_path(request),
                success=True,
                status_code=200,
                model_used=model_used,
                test_type=str(ctx.get("test_type") or ""),
                module_id=ctx.get("module_id"),
                streamed=False,
                latency_ms=int((time.monotonic() - started_at) * 1000),
                prompt_chars=len(str(ctx.get("requirement") or ""))
                + len(str(ctx.get("api_spec") or "")),
                output_chars=len(
                    json.dumps(resp_payload.get("cases") or [], ensure_ascii=False)
                ),
                cases_count=len(resp_payload.get("cases") or []),
                meta={
                    "dedup_debug": bool(ctx.get("dedup_debug")),
                    "run_id": run_id,
                    "prompt_version": "v1",
                },
            )
        finally:
            if slot:
                release_ai_concurrency_slot(
                    user_id=int(getattr(request.user, "id", 0) or 0)
                )
        return resp


class AiPhase1PreviewAPIView(APIView):
    """
    POST /api/ai/phase1-preview/
    仅执行 Phase1 意图分析，返回「推导模块」与「关键测试点」等，供前端确认后再正式生成。
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        started_at = time.monotonic()
        slot, denied = _guard_ai_request_or_429(request, action="phase1_preview")
        if denied is not None:
            return denied
        ctx, err = _prepare_ai_generate_context(request)
        if err:
            resp = Response(
                {"success": False, "error": err, "message": err, "data": None},
                status=400,
            )
            try:
                write_ai_usage_event(
                    user=request.user,
                    action="phase1_preview",
                    endpoint=_request_path(request),
                    success=False,
                    status_code=400,
                    streamed=False,
                    latency_ms=int((time.monotonic() - started_at) * 1000),
                    error_code="INVALID_INPUT",
                    error_message=err,
                )
            finally:
                if slot:
                    release_ai_concurrency_slot(
                        user_id=int(getattr(request.user, "id", 0) or 0)
                    )
            return resp
        if not OPENAI_SDK_AVAILABLE:
            msg = _openai_missing_response_json()
            resp = Response(
                {"success": False, "error": msg, "message": msg, "data": None},
                status=503,
            )
            try:
                write_ai_usage_event(
                    user=request.user,
                    action="phase1_preview",
                    endpoint=_request_path(request),
                    success=False,
                    status_code=503,
                    streamed=False,
                    latency_ms=int((time.monotonic() - started_at) * 1000),
                    error_code="SDK_NOT_AVAILABLE",
                    error_message="OpenAI SDK 不可用",
                )
            finally:
                if slot:
                    release_ai_concurrency_slot(
                        user_id=int(getattr(request.user, "id", 0) or 0)
                    )
            return resp

        api_key = ctx["api_key"]
        api_base_url = ctx["api_base_url"]
        model_used = ctx["model_used"]
        try:
            _debug_log_openai_target("ai_phase1_preview_sdk", model_used, api_base_url)
            client = OpenAI(api_key=api_key, base_url=api_base_url, timeout=60.0)
            phase1 = _run_phase1_intent_analysis(
                client,
                model_used=model_used,
                requirement=str(ctx.get("requirement") or ""),
                fallback_module=str(ctx.get("module_name") or ""),
            )
        except Exception as e:
            handled = resolve_ai_generate_cases_outer_openai_error(
                e,
                request=request,
                model_used=model_used,
                api_base_url=api_base_url,
                module_id=ctx.get("module_id"),
                fail=lambda m, status_code=400, code="PHASE1_FAILED": Response(
                    {
                        "success": False,
                        "error": m,
                        "message": m,
                        "code": code,
                        "data": None,
                    },
                    status=status_code,
                ),
            )
            if handled is not None:
                return handled
            return Response(
                {
                    "success": False,
                    "error": str(e),
                    "message": "Phase1 分析失败",
                    "data": None,
                },
                status=500,
            )

        module_name = str(phase1.get("module_name") or "").strip() or "通用功能模块"
        points_raw = phase1.get("key_test_points")
        points = (
            [str(x).strip() for x in points_raw if str(x).strip()]
            if isinstance(points_raw, list)
            else []
        )
        out = {
            "module_name": module_name,
            "key_test_points": points,
            "raw": phase1,
            "model": model_used,
        }
        resp = Response({"success": True, "message": "ok", "data": out}, status=200)
        try:
            write_ai_usage_event(
                user=request.user,
                action="phase1_preview",
                endpoint=_request_path(request),
                success=True,
                status_code=200,
                model_used=str(out.get("model") or ""),
                test_type=str(ctx.get("test_type") or ""),
                module_id=ctx.get("module_id"),
                streamed=False,
                latency_ms=int((time.monotonic() - started_at) * 1000),
                prompt_chars=len(str(ctx.get("requirement") or ""))
                + len(str(ctx.get("api_spec") or "")),
                output_chars=len(json.dumps(out or {}, ensure_ascii=False)),
            )
        finally:
            if slot:
                release_ai_concurrency_slot(
                    user_id=int(getattr(request.user, "id", 0) or 0)
                )
        return resp


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

        # AI 治理：进入长连接前先做配额与并发校验（拒绝则直接返回 429）
        slot, denied = _guard_ai_request_or_429(
            drf_request, action="generate_cases_stream"
        )
        if denied is not None:
            try:
                data = getattr(denied, "data", None)
            except Exception:
                data = None
            return JsonResponse(
                data
                or {
                    "success": False,
                    "error": "AI 请求被限流/配额阻断",
                    "cases": [],
                    "message": "限流",
                },
                status=429,
            )

        api_key = ctx["api_key"]
        api_base_url = ctx["api_base_url"]
        model_used = ctx["model_used"]
        module_id = ctx.get("module_id")
        disp = dispatch_ai_generation(ctx)
        use_api = disp.should_enrich_api
        user_msg = disp.user_message

        phase1_override = None
        try:
            if isinstance(getattr(drf_request, "data", None), dict):
                p1o = drf_request.data.get("phase1_override")
                if isinstance(p1o, dict):
                    phase1_override = p1o
        except Exception:
            phase1_override = None

        def event_stream():
            stream_started_at = time.monotonic()
            payload = getattr(drf_request, "data", None)
            raw_parts_outer: list[str] = []
            audit_success = False
            audit_all_covered = False
            audit_cases_count = 0
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
                phase1_client = OpenAI(
                    api_key=api_key, base_url=api_base_url, timeout=90.0
                )
                if phase1_override is not None:
                    phase1 = phase1_override
                else:
                    phase1 = _run_phase1_intent_analysis(
                        phase1_client,
                        model_used=model_used,
                        requirement=str(ctx.get("requirement") or ""),
                        fallback_module=str(ctx.get("module_name") or ""),
                    )
                phase1_module_name = str(
                    phase1.get("module_name") or ""
                ).strip() or str(ctx.get("module_name") or "")
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
            stream_phase2_system_prompt = (
                stream_system_prompt + "\n\n" + _PHASE2_MULTI_CASE_MANDATE
            )
            effective_module_id, effective_module_name = _resolve_effective_module(
                module_id=module_id,
                ctx_module_name=str(ctx.get("module_name") or ""),
                phase1_module_name=phase1_module_name,
                test_type=str(ctx.get("test_type") or ""),
            )
            existing_rows: list[dict] = []
            existing_titles: list[str] = []
            try:
                existing_rows, existing_titles = _load_existing_case_context(
                    module_id=effective_module_id,
                    test_type=str(ctx.get("test_type") or ""),
                )
            except Exception:
                logger.exception("读取已有用例失败（流式），跳过前置规避提示")
            stream_batch_user_prompt = build_batch_generation_prompt(
                module_name=effective_module_name
                or phase1_module_name
                or str(ctx.get("module_name") or ""),
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
            raw_parts = raw_parts_outer
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
                    {
                        "type": "error",
                        "code": "AUTH_ERROR",
                        "message": f"API Key 无效：{e}",
                        "detail": str(e),
                    }
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
                    audit_success = True
                    audit_all_covered = True
                    audit_cases_count = 0
                    return

                try:
                    parsed = parse_batch_json_array(raw)
                except Exception:
                    parsed = _parse_ai_cases_json(raw)
                if not parsed:
                    snippet = raw[:400] + ("…" if len(raw) > 400 else "")
                    failure_fragment = (
                        raw[-800:]
                        if len(raw) > 800 and truncate_by_length
                        else raw[:800]
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
                dedup_mode = (
                    str(
                        ctx.get("dedup_mode")
                        or drf_request.data.get("dedup_mode")
                        or "drop"
                    )
                    if isinstance(getattr(drf_request, "data", None), dict)
                    else "drop"
                )
                cases, dedup_debug_report = _apply_dedup_pipeline(
                    cases=cases,
                    existing_titles=existing_titles,
                    existing_rows=existing_rows,
                    api_key=api_key,
                    base_url=api_base_url,
                    debug=bool(ctx.get("dedup_debug")),
                    mode=dedup_mode,
                )
                if use_api and cases:
                    renumber_api_business_ids(cases)
                retry_round = 0
                while (
                    len(cases) < AI_GENERATE_MIN_CASES
                    and retry_round < AI_GENERATE_RETRY_ROUNDS
                ):
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
                _backfill_case_module_names(
                    cases,
                    effective_module_name,
                    phase1_module_name,
                    str(ctx.get("module_name") or ""),
                )
                if use_api and cases:
                    backfill_api_request_fields_in_batch(cases)
            except Exception as parse_err:
                logger.exception(
                    "AI stream phase2 parse/normalize failed: %s", parse_err
                )
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

            done_payload = {
                "type": "done",
                "success": True,
                "phase1_analysis": phase1,
                "message": f"已生成 {len(cases)} 条用例",
                "cases": cases,
                "model": model_used,
            }
            if ctx.get("dedup_debug"):
                done_payload["dedup_debug"] = dedup_debug_report
            run_id = _write_ai_case_generation_run(
                user=drf_request.user,
                action="generate_cases_stream",
                ctx=ctx,
                model_used=model_used,
                phase1=phase1,
                phase1_override=(
                    payload.get("phase1_override")
                    if isinstance(payload, dict)
                    else None
                ),
                streamed=True,
                success=True,
                all_covered=False,
                cases_count=len(cases),
                latency_ms=int((time.monotonic() - stream_started_at) * 1000),
                output_chars=len("".join(raw_parts_outer)),
                meta={
                    "truncated_by_length": bool(truncate_by_length),
                    "dedup_debug": bool(ctx.get("dedup_debug")),
                    "prompt_version": "v1",
                },
            )
            done_payload["run_id"] = run_id
            audit_success = True
            audit_all_covered = False
            audit_cases_count = len(cases)
            yield _sse_event(done_payload)
            try:
                write_ai_usage_event(
                    user=drf_request.user,
                    action="generate_cases_stream",
                    endpoint=_request_path(request),
                    success=bool(audit_success),
                    status_code=200 if audit_success else 500,
                    model_used=model_used,
                    test_type=str(ctx.get("test_type") or ""),
                    module_id=ctx.get("module_id"),
                    streamed=True,
                    all_covered=bool(audit_all_covered),
                    latency_ms=int((time.monotonic() - stream_started_at) * 1000),
                    prompt_chars=len(str(ctx.get("requirement") or ""))
                    + len(str(ctx.get("api_spec") or "")),
                    output_chars=len("".join(raw_parts_outer)),
                    cases_count=int(audit_cases_count),
                    meta={
                        "truncated_by_length": bool(truncate_by_length),
                        "run_id": run_id,
                        "prompt_version": "v1",
                    },
                )
            except Exception:
                pass
            if slot:
                release_ai_concurrency_slot(
                    user_id=int(getattr(drf_request.user, "id", 0) or 0)
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


class AiSuggestCaseFixAPIView(APIView):
    """
    POST /api/ai/suggest-case-fix/
    基于单条 ExecutionLog（未通过）生成用例修订建议；不落库，须项目成员等数据权限。
    Body: { "execution_log_id": int, "hint"?: str }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from testcase.models import ExecutionLog, TestCaseStep

        from assistant.services.case_fix_from_execution import (
            CASE_FIX_SYSTEM_PROMPT,
            build_case_fix_user_message,
            can_user_access_execution_log,
            parse_case_fix_llm_output,
        )

        started_at = time.monotonic()
        slot, denied = _guard_ai_request_or_429(request, action="suggest_case_fix")
        if denied is not None:
            return denied

        body = request.data if isinstance(request.data, dict) else {}
        el_raw = body.get("execution_log_id")
        try:
            el_id = int(el_raw)
        except (TypeError, ValueError):
            return Response(
                {"success": False, "message": "execution_log_id 必填且为整数"},
                status=400,
            )

        log = (
            ExecutionLog.objects.select_related(
                "test_case__module__project", "test_case__creator"
            )
            .filter(pk=el_id, is_deleted=False)
            .first()
        )
        if not log:
            try:
                if slot:
                    release_ai_concurrency_slot(
                        user_id=int(getattr(request.user, "id", 0) or 0)
                    )
            except Exception:
                pass
            return Response({"success": False, "message": "执行日志不存在"}, status=404)

        if not can_user_access_execution_log(request.user, log):
            try:
                if slot:
                    release_ai_concurrency_slot(
                        user_id=int(getattr(request.user, "id", 0) or 0)
                    )
            except Exception:
                pass
            return Response({"success": False, "message": "无权限查看该执行记录"}, status=403)

        if bool(log.is_passed):
            try:
                if slot:
                    release_ai_concurrency_slot(
                        user_id=int(getattr(request.user, "id", 0) or 0)
                    )
            except Exception:
                pass
            return Response(
                {
                    "success": False,
                    "message": "该条执行记录为通过状态，无需生成修订建议",
                    "summary": "",
                    "suggested_steps": [],
                    "risks": "",
                },
                status=400,
            )

        tc = log.test_case
        if not tc or getattr(tc, "is_deleted", False):
            try:
                if slot:
                    release_ai_concurrency_slot(
                        user_id=int(getattr(request.user, "id", 0) or 0)
                    )
            except Exception:
                pass
            return Response({"success": False, "message": "关联用例不存在"}, status=404)

        steps = list(
            TestCaseStep.objects.filter(testcase=tc, is_deleted=False)
            .order_by("step_number")
            .values("step_number", "step_desc", "expected_result")[:80]
        )
        steps_lines = []
        for s in steps:
            steps_lines.append(
                f"{s['step_number']}. {(s.get('step_desc') or '').strip()} => 预期: {(s.get('expected_result') or '—')}"
            )
        steps_block = "\n".join(steps_lines) if steps_lines else "（无步骤）"

        hint = str(body.get("hint") or body.get("extra_hint") or "").strip()[:2000]
        user_msg = build_case_fix_user_message(
            case_name=str(tc.case_name or ""),
            test_type=str(tc.test_type or ""),
            steps_block=steps_block,
            execution_status=str(log.execution_status or ""),
            is_passed=bool(log.is_passed),
            request_method=str(log.request_method or ""),
            request_url=str(log.request_url or "")[:2048],
            response_status=log.response_status_code,
            error_message=str(log.error_message or "")[:4000],
            assertion_text=json.dumps(log.assertion_results or [], ensure_ascii=False)[
                :4000
            ],
            request_body_snip=str(log.request_body_text or "")[:3500],
            response_body_snip=str(log.response_body_text or "")[:3500],
            extra_hint=hint,
        )

        api_key, api_base_url, model_used = _get_active_ai_model_credentials()
        if not api_key or not OPENAI_SDK_AVAILABLE:
            try:
                if slot:
                    release_ai_concurrency_slot(
                        user_id=int(getattr(request.user, "id", 0) or 0)
                    )
            except Exception:
                pass
            return Response(
                {
                    "success": False,
                    "message": _openai_missing_response_json()
                    if not OPENAI_SDK_AVAILABLE
                    else "未配置已连通的全局 AI（请在系统管理中连接模型）",
                },
                status=503,
            )

        parsed: dict = {}
        err_msg = ""
        try:
            _debug_log_openai_target("ai_suggest_case_fix", model_used, api_base_url)
            client = OpenAI(api_key=api_key, base_url=api_base_url, timeout=60.0)
            completion = client.chat.completions.create(
                model=model_used,
                messages=[
                    {"role": "system", "content": CASE_FIX_SYSTEM_PROMPT},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.2,
                max_tokens=1800,
            )
            raw = (completion.choices[0].message.content or "").strip()
            parsed = parse_case_fix_llm_output(raw)
        except Exception as e:
            err_msg = str(e)
            logger.exception(
                "suggest_case_fix failed. user_id=%s log_id=%s",
                getattr(request.user, "id", None),
                el_id,
            )

        latency_ms = int((time.monotonic() - started_at) * 1000)
        try:
            write_ai_usage_event(
                user=request.user,
                action="suggest_case_fix",
                endpoint=_request_path(request),
                success=bool(parsed and not err_msg),
                status_code=200 if (parsed and not err_msg) else 502,
                model_used=str(model_used or ""),
                test_type=str(tc.test_type or ""),
                module_id=getattr(getattr(tc, "module", None), "id", None),
                streamed=False,
                latency_ms=latency_ms,
                prompt_chars=len(user_msg),
                output_chars=len(json.dumps(parsed, ensure_ascii=False)) if parsed else 0,
                error_code="" if not err_msg else "PARSE_OR_UPSTREAM",
                error_message=err_msg[:512] if err_msg else "",
                meta={"execution_log_id": el_id, "test_case_id": tc.id},
            )
        except Exception:
            pass
        try:
            if slot:
                release_ai_concurrency_slot(
                    user_id=int(getattr(request.user, "id", 0) or 0)
                )
        except Exception:
            pass

        if err_msg or not parsed:
            return Response(
                {
                    "success": False,
                    "message": err_msg or "模型输出解析失败",
                    "summary": "",
                    "suggested_steps": [],
                    "risks": "请稍后重试或检查模型输出是否为合法 JSON。",
                },
                status=502,
            )

        return Response(
            {
                "success": True,
                "execution_log_id": el_id,
                "test_case_id": tc.id,
                "model": model_used,
                **parsed,
            },
            status=200,
        )


def _can_user_access_test_case(user, tc) -> bool:
    """与 ExecutionLog 访问权限口径一致：项目成员 / 系统管理员 / 创建者（含无 module 的孤儿用例）。"""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
        return True
    if bool(getattr(user, "is_system_admin", False)):
        return True
    if not tc or getattr(tc, "is_deleted", False):
        return False
    mod = getattr(tc, "module", None)
    if mod is None:
        return int(getattr(tc, "creator_id", 0) or 0) == int(getattr(user, "id", 0) or 0)
    proj = getattr(mod, "project", None)
    if not proj or getattr(proj, "is_deleted", False):
        return False
    if proj.members.filter(pk=user.pk, is_deleted=False).exists():
        return True
    return int(getattr(tc, "creator_id", 0) or 0) == int(getattr(user, "id", 0) or 0)


def _case_steps_snapshot(tc) -> list[dict]:
    from testcase.models import TestCaseStep

    rows = list(
        TestCaseStep.objects.filter(testcase=tc, is_deleted=False)
        .order_by("step_number")
        .values("step_number", "step_desc", "expected_result")[:120]
    )
    out = []
    for r in rows:
        out.append(
            {
                "step_number": int(r.get("step_number") or 0),
                "step_desc": str(r.get("step_desc") or ""),
                "expected_result": str(r.get("expected_result") or "—"),
            }
        )
    return out


class AiPatchFromExecutionAPIView(APIView):
    """
    POST /api/ai/patches/from-execution/
    基于未通过 ExecutionLog 生成 AiPatch（默认 draft，不自动写入用例）。

    body: { "execution_log_id": int, "hint"?: str }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from assistant.models import AiPatch
        from testcase.models import ExecutionLog
        from assistant.services.case_fix_from_execution import (
            can_user_access_execution_log,
        )
        from common.services.audit import record_audit_event
        from common.models import AuditEvent

        body = request.data if isinstance(request.data, dict) else {}
        try:
            el_id = int(body.get("execution_log_id"))
        except (TypeError, ValueError):
            return Response({"success": False, "message": "execution_log_id 必填且为整数"}, status=400)

        # 复用现有建议生成接口逻辑：直接调用内部 view 并解析返回
        # 这里为了最小改动，走同一段逻辑：调用 LLM 生成 suggested_steps。
        # （后续可重构为 service 复用，避免重复耗时）
        suggest_view = AiSuggestCaseFixAPIView()
        suggest_view.request = request
        suggest_resp = suggest_view.post(request)
        if getattr(suggest_resp, "status_code", 500) != 200:
            return suggest_resp
        payload = suggest_resp.data if isinstance(suggest_resp.data, dict) else {}

        log = (
            ExecutionLog.objects.select_related("test_case__module__project", "test_case__creator")
            .filter(pk=el_id, is_deleted=False)
            .first()
        )
        if not log:
            return Response({"success": False, "message": "执行日志不存在"}, status=404)
        if not can_user_access_execution_log(request.user, log):
            return Response({"success": False, "message": "无权限查看该执行记录"}, status=403)
        if bool(log.is_passed):
            return Response({"success": False, "message": "仅允许基于未通过的执行记录生成补丁"}, status=400)

        tc = log.test_case
        if not tc or getattr(tc, "is_deleted", False):
            return Response({"success": False, "message": "关联用例不存在"}, status=404)

        before_steps = _case_steps_snapshot(tc)
        after_steps = payload.get("suggested_steps") or []
        if not isinstance(after_steps, list):
            after_steps = []

        # 粗略风险：步骤为空或变化过大标 high
        risk = AiPatch.RISK_MEDIUM
        if not after_steps:
            risk = AiPatch.RISK_HIGH
        elif len(after_steps) >= 2 * max(1, len(before_steps)):
            risk = AiPatch.RISK_HIGH
        elif len(after_steps) <= max(1, len(before_steps) // 2):
            risk = AiPatch.RISK_HIGH

        patch = AiPatch.objects.create(
            creator=request.user,
            target_type="testcase.TestCase",
            target_id=str(tc.id),
            source_execution_log_id=int(el_id),
            status=AiPatch.STATUS_DRAFT,
            risk_level=risk,
            summary=str(payload.get("summary") or "")[:512],
            risks=str(payload.get("risks") or "")[:1000],
            before={"steps": before_steps},
            after={"steps": after_steps},
            changes=[
                {"op": "replace_all_steps", "count_before": len(before_steps), "count_after": len(after_steps)}
            ],
        )

        record_audit_event(
            action=AuditEvent.ACTION_EXECUTE,
            actor=request.user,
            instance=patch,
            request=request,
            extra={
                "ai_patch_id": patch.id,
                "target_type": patch.target_type,
                "target_id": patch.target_id,
                "source_execution_log_id": el_id,
            },
        )

        return Response(
            {
                "success": True,
                "patch_id": patch.id,
                "status": patch.status,
                "risk_level": patch.risk_level,
                "target_type": patch.target_type,
                "target_id": patch.target_id,
                "summary": patch.summary,
                "risks": patch.risks,
                "before": patch.before,
                "after": patch.after,
                "changes": patch.changes,
            }
        )


class AiPatchApplyAPIView(APIView):
    """
    POST /api/ai/patches/<id>/apply/
    body: { "confirm": true }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, patch_id: int):
        from assistant.models import AiPatch
        from testcase.models import TestCase, TestCaseStep
        from common.services.audit import record_audit_event
        from common.models import AuditEvent

        patch = AiPatch.objects.filter(pk=patch_id).first()
        if not patch:
            return Response({"success": False, "message": "patch 不存在"}, status=404)
        if patch.status != AiPatch.STATUS_DRAFT:
            return Response({"success": False, "message": "仅允许对 draft 补丁执行 apply"}, status=400)
        if not isinstance(request.data, dict) or request.data.get("confirm") is not True:
            return Response({"success": False, "message": "须将 confirm 设为布尔 true 以确认应用"}, status=400)
        if patch.target_type != "testcase.TestCase":
            return Response({"success": False, "message": "当前仅支持 testcase.TestCase 的补丁"}, status=400)

        tc = (
            TestCase.objects.select_related("module__project", "creator")
            .filter(pk=int(patch.target_id), is_deleted=False)
            .first()
        )
        if not tc:
            return Response({"success": False, "message": "目标用例不存在"}, status=404)
        if not _can_user_access_test_case(request.user, tc):
            return Response({"success": False, "message": "无权限操作该用例"}, status=403)

        after_steps = (patch.after or {}).get("steps") if isinstance(patch.after, dict) else None
        if not isinstance(after_steps, list) or not after_steps:
            return Response({"success": False, "message": "补丁 after.steps 为空，无法应用"}, status=400)

        before_snapshot = _case_steps_snapshot(tc)
        with transaction.atomic():
            TestCaseStep.objects.filter(testcase=tc, is_deleted=False).update(is_deleted=True)
            for idx, it in enumerate(after_steps[:60], start=1):
                if not isinstance(it, dict):
                    continue
                desc = str(it.get("step_desc") or it.get("desc") or "").strip()
                exp = str(it.get("expected_result") or it.get("expected") or "").strip() or "—"
                if not desc:
                    continue
                TestCaseStep.objects.create(
                    testcase=tc,
                    step_number=idx,
                    step_desc=desc[:4000],
                    expected_result=exp[:2000],
                    creator=request.user,
                    updater=request.user,
                )
            tc.save(update_fields=["update_time"])
            patch.before = patch.before or {}
            if isinstance(patch.before, dict):
                patch.before["steps"] = before_snapshot
            patch.status = AiPatch.STATUS_APPLIED
            patch.applied_at = timezone.now()
            patch.save(update_fields=["before", "status", "applied_at", "updated_at"])

        record_audit_event(
            action=AuditEvent.ACTION_UPDATE,
            actor=request.user,
            instance=tc,
            request=request,
            extra={"ai_patch_id": patch.id, "operation": "apply", "steps": len(after_steps)},
        )
        return Response({"success": True, "message": "已应用补丁", "patch_id": patch.id, "test_case_id": tc.id})


class AiPatchRollbackAPIView(APIView):
    """
    POST /api/ai/patches/<id>/rollback/
    body: { "confirm": true }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, patch_id: int):
        from assistant.models import AiPatch
        from testcase.models import TestCase, TestCaseStep
        from common.services.audit import record_audit_event
        from common.models import AuditEvent

        patch = AiPatch.objects.filter(pk=patch_id).first()
        if not patch:
            return Response({"success": False, "message": "patch 不存在"}, status=404)
        if patch.status != AiPatch.STATUS_APPLIED:
            return Response({"success": False, "message": "仅允许对 applied 补丁执行 rollback"}, status=400)
        if not isinstance(request.data, dict) or request.data.get("confirm") is not True:
            return Response({"success": False, "message": "须将 confirm 设为布尔 true 以确认回滚"}, status=400)
        if patch.target_type != "testcase.TestCase":
            return Response({"success": False, "message": "当前仅支持 testcase.TestCase 的补丁"}, status=400)

        tc = (
            TestCase.objects.select_related("module__project", "creator")
            .filter(pk=int(patch.target_id), is_deleted=False)
            .first()
        )
        if not tc:
            return Response({"success": False, "message": "目标用例不存在"}, status=404)
        if not _can_user_access_test_case(request.user, tc):
            return Response({"success": False, "message": "无权限操作该用例"}, status=403)

        before_steps = (patch.before or {}).get("steps") if isinstance(patch.before, dict) else None
        if not isinstance(before_steps, list):
            before_steps = []

        with transaction.atomic():
            TestCaseStep.objects.filter(testcase=tc, is_deleted=False).update(is_deleted=True)
            for idx, it in enumerate(before_steps[:60], start=1):
                if not isinstance(it, dict):
                    continue
                desc = str(it.get("step_desc") or "").strip()
                exp = str(it.get("expected_result") or "").strip() or "—"
                if not desc:
                    continue
                TestCaseStep.objects.create(
                    testcase=tc,
                    step_number=idx,
                    step_desc=desc[:4000],
                    expected_result=exp[:2000],
                    creator=request.user,
                    updater=request.user,
                )
            tc.save(update_fields=["update_time"])
            patch.status = AiPatch.STATUS_ROLLED_BACK
            patch.rolled_back_at = timezone.now()
            patch.save(update_fields=["status", "rolled_back_at", "updated_at"])

        record_audit_event(
            action=AuditEvent.ACTION_UPDATE,
            actor=request.user,
            instance=tc,
            request=request,
            extra={"ai_patch_id": patch.id, "operation": "rollback", "steps": len(before_steps)},
        )
        return Response({"success": True, "message": "已回滚补丁", "patch_id": patch.id, "test_case_id": tc.id})


class AiPatchListAPIView(APIView):
    """
    GET /api/ai/patches/?target_type=&target_id=&status=&page=&page_size=
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from assistant.models import AiPatch

        target_type = str(request.query_params.get("target_type") or "").strip()
        target_id = str(request.query_params.get("target_id") or "").strip()
        status_q = str(request.query_params.get("status") or "").strip()

        try:
            page = int(request.query_params.get("page") or 1)
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(request.query_params.get("page_size") or 20)
        except (TypeError, ValueError):
            page_size = 20
        page = max(1, page)
        page_size = max(1, min(page_size, 200))
        offset = (page - 1) * page_size

        qs = AiPatch.objects.all()
        if target_type:
            qs = qs.filter(target_type=target_type)
        if target_id:
            qs = qs.filter(target_id=target_id)
        if status_q:
            qs = qs.filter(status=status_q)

        total = qs.count()
        rows = list(
            qs.order_by("-created_at")
            .values(
                "id",
                "target_type",
                "target_id",
                "status",
                "risk_level",
                "summary",
                "risks",
                "source_execution_log_id",
                "creator_id",
                "created_at",
                "applied_at",
                "rolled_back_at",
            )[offset : offset + page_size]
        )
        return Response({"success": True, "page": page, "page_size": page_size, "total": total, "items": rows})


class AiSecurityGenerateCasesAPIView(APIView):
    """
    POST /api/ai/security/generate-cases/
    基于 OpenAPI 生成安全用例草稿（规则优先，不依赖大模型）。

    body:
    - openapi_spec: string（JSON/YAML）
    - base_url?: string
    - scope?: string[]（可选：idor/injection/sensitive/authn）
    - max_findings?: number（默认 50，最大 200）
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from assistant.services.security_rules import generate_security_findings_from_openapi
        from assistant.services.ai_governance import write_ai_usage_event

        started = time.monotonic()
        slot, denied = _guard_ai_request_or_429(request, action="security_generate")
        if denied is not None:
            return denied

        body = request.data if isinstance(request.data, dict) else {}
        spec = str(body.get("openapi_spec") or body.get("openapi") or "").strip()
        if not spec:
            try:
                if slot:
                    release_ai_concurrency_slot(user_id=int(getattr(request.user, "id", 0) or 0))
            except Exception:
                pass
            return Response({"success": False, "message": "openapi_spec 必填"}, status=400)

        base_url = str(body.get("base_url") or "").strip()
        scope = body.get("scope")
        scopes = scope if isinstance(scope, list) else []
        max_findings = body.get("max_findings", 50)
        try:
            max_findings = int(max_findings)
        except (TypeError, ValueError):
            max_findings = 50
        max_findings = max(1, min(max_findings, 200))

        findings: list[dict] = []
        err = ""
        try:
            findings = generate_security_findings_from_openapi(
                openapi_spec_text=spec,
                base_url=base_url,
                scopes=[str(x) for x in scopes],
                max_findings=max_findings,
            )
        except Exception as exc:
            err = str(exc)

        latency_ms = int((time.monotonic() - started) * 1000)
        try:
            write_ai_usage_event(
                user=request.user,
                action="security_generate",
                endpoint=_request_path(request),
                success=bool(findings) and not err,
                status_code=200 if (findings and not err) else 400,
                model_used="rule_engine",
                test_type="security",
                module_id=None,
                streamed=False,
                latency_ms=latency_ms,
                prompt_chars=len(spec),
                output_chars=len(json.dumps(findings, ensure_ascii=False)) if findings else 0,
                cases_count=len(findings),
                error_code="" if not err else "RULE_ENGINE",
                error_message=err[:512] if err else "",
                meta={"scopes": scopes, "max_findings": max_findings},
            )
        except Exception:
            pass
        try:
            if slot:
                release_ai_concurrency_slot(user_id=int(getattr(request.user, "id", 0) or 0))
        except Exception:
            pass

        if err:
            return Response({"success": False, "message": err, "findings": []}, status=400)
        return Response({"success": True, "findings": findings, "engine": "rule_engine"})


class AiSecurityAnalyzeExecutionAPIView(APIView):
    """
    POST /api/ai/security/analyze-execution/
    基于单条 ExecutionLog 做轻量安全信号分析（规则/启发式，不等价于渗透）。

    body:
    - execution_log_id: int
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from testcase.models import ExecutionLog
        from assistant.services.case_fix_from_execution import can_user_access_execution_log
        from assistant.services.security_rules import analyze_execution_log_security
        from assistant.services.ai_governance import write_ai_usage_event

        started = time.monotonic()
        slot, denied = _guard_ai_request_or_429(request, action="security_analyze")
        if denied is not None:
            return denied

        body = request.data if isinstance(request.data, dict) else {}
        try:
            el_id = int(body.get("execution_log_id"))
        except (TypeError, ValueError):
            return Response({"success": False, "message": "execution_log_id 必填且为整数"}, status=400)

        log = (
            ExecutionLog.objects.select_related("test_case__module__project", "test_case__creator")
            .filter(pk=el_id, is_deleted=False)
            .first()
        )
        if not log:
            return Response({"success": False, "message": "执行日志不存在"}, status=404)
        if not can_user_access_execution_log(request.user, log):
            return Response({"success": False, "message": "无权限查看该执行记录"}, status=403)

        findings = analyze_execution_log_security(
            response_status=getattr(log, "response_status_code", None),
            response_text=str(getattr(log, "response_body_text", "") or ""),
            response_headers=getattr(log, "response_headers", None) if hasattr(log, "response_headers") else {},
        )

        latency_ms = int((time.monotonic() - started) * 1000)
        try:
            tc = getattr(log, "test_case", None)
            write_ai_usage_event(
                user=request.user,
                action="security_analyze",
                endpoint=_request_path(request),
                success=True,
                status_code=200,
                model_used="rule_engine",
                test_type="security",
                module_id=getattr(getattr(tc, "module", None), "id", None),
                streamed=False,
                latency_ms=latency_ms,
                prompt_chars=0,
                output_chars=len(json.dumps(findings, ensure_ascii=False)),
                cases_count=len(findings),
                error_code="",
                error_message="",
                meta={"execution_log_id": int(el_id), "test_case_id": getattr(tc, "id", None)},
            )
        except Exception:
            pass
        try:
            if slot:
                release_ai_concurrency_slot(user_id=int(getattr(request.user, "id", 0) or 0))
        except Exception:
            pass

        return Response({"success": True, "execution_log_id": int(el_id), "findings": findings, "engine": "rule_engine"})


class AiKnowledgeAskAPIView(APIView):
    """
    POST /api/ai/knowledge/ask/
    企业知识库可追溯问答：返回 answer_markdown + citations[]。

    body:
    - question: string（必填）
    - project_id?: int（可选；提供后会额外检索该项目内的用例/缺陷，并作为 citations 返回）
    - top_k?: number（默认 5，最大 10）
    - category?: string（可选）
    - tag?: string（可选）
    - min_score?: float（可选）
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        started_at = time.monotonic()
        slot, denied = _guard_ai_request_or_429(request, action="knowledge_ask")
        if denied is not None:
            return denied

        body = request.data if isinstance(request.data, dict) else {}
        q = str(body.get("question") or body.get("query") or "").strip()
        if not q:
            try:
                if slot:
                    release_ai_concurrency_slot(user_id=int(getattr(request.user, "id", 0) or 0))
            except Exception:
                pass
            return Response({"success": False, "message": "question 不能为空", "answer_markdown": "", "citations": []}, status=400)

        top_k = body.get("top_k", 5)
        try:
            top_k = int(top_k)
        except (TypeError, ValueError):
            top_k = 5
        top_k = max(1, min(top_k, 10))
        category = (body.get("category") or "").strip() or None
        tag = (body.get("tag") or "").strip() or None
        raw_min_score = body.get("min_score")
        min_score = None
        if raw_min_score not in (None, ""):
            try:
                min_score = float(raw_min_score)
            except (TypeError, ValueError):
                min_score = None

        results = KnowledgeSearcher.search_similar(
            q,
            top_k=top_k,
            category=category,
            tag=tag,
            min_score=min_score,
        )

        citations = []
        ctx_blocks = []

        # 1) 知识文章 citations
        for i, r in enumerate(results, start=1):
            aid = r.get("article_id")
            title = str(r.get("title") or f"KnowledgeArticle#{aid or ''}").strip()
            idx = len(citations) + 1
            citations.append(
                {
                    "idx": idx,
                    "type": "doc",
                    "id": int(aid) if aid is not None else None,
                    "title": title,
                    "url": f"/knowledge?article_id={aid}" if aid is not None else "/knowledge",
                    "category": r.get("category") or "",
                    "tags": r.get("tags") or [],
                    "retrieve_mode": r.get("retrieve_mode") or "",
                    "score": r.get("score"),
                }
            )
            doc = str(r.get("document") or "")[:4000]
            ctx_blocks.append(f"[C{idx}] (doc) {title}\n{doc}")

        # 2) 可选：项目内用例/缺陷检索
        project_id = body.get("project_id")
        pid = None
        if project_id not in (None, ""):
            try:
                pid = int(project_id)
            except (TypeError, ValueError):
                pid = None
        if pid is not None:
            from project.models import TestProject
            from testcase.models import TestCase
            from defect.models import TestDefect

            proj = TestProject.objects.filter(pk=pid, is_deleted=False).first()
            if proj:
                can = (
                    getattr(request.user, "is_system_admin", False)
                    or getattr(request.user, "is_superuser", False)
                    or getattr(request.user, "is_staff", False)
                    or proj.members.filter(pk=request.user.pk, is_deleted=False).exists()
                )
                if can:
                    # 用例：标题匹配
                    case_qs = (
                        TestCase.objects.filter(is_deleted=False, module__project_id=int(pid))
                        .filter(case_name__icontains=q)
                        .order_by("-id")[:5]
                        .values("id", "case_name", "test_type")
                    )
                    for r in list(case_qs):
                        cid = int(r["id"])
                        tt = str(r.get("test_type") or "").strip() or "functional"
                        # api 特殊路由：/test-case/api
                        url = (
                            f"/test-case/api?case_id={cid}"
                            if tt == "api"
                            else f"/test-case/{tt}?case_id={cid}"
                        )
                        idx = len(citations) + 1
                        title = str(r.get("case_name") or f"TestCase#{cid}")
                        citations.append({"idx": idx, "type": "case", "id": cid, "title": title, "url": url})
                        ctx_blocks.append(f"[C{idx}] (case) id={cid} test_type={tt} title={title}")

                    defect_qs = (
                        TestDefect.objects.filter(is_deleted=False, module__project_id=int(pid))
                        .filter(defect_name__icontains=q)
                        .order_by("-id")[:5]
                        .values("id", "defect_no", "defect_name", "severity", "status")
                    )
                    for r in list(defect_qs):
                        did = int(r["id"])
                        title = str(r.get("defect_name") or f"Defect#{did}")
                        no = str(r.get("defect_no") or "")
                        url = f"/defect/detail/{did}"
                        idx = len(citations) + 1
                        citations.append(
                            {
                                "idx": idx,
                                "type": "defect",
                                "id": did,
                                "title": title,
                                "defect_no": no,
                                "severity": r.get("severity"),
                                "status": r.get("status"),
                                "url": url,
                            }
                        )
                        ctx_blocks.append(f"[C{idx}] (defect) {no} title={title} severity={r.get('severity')} status={r.get('status')}")

        api_key, api_base_url, model_used = _get_active_ai_model_credentials()
        if not api_key or not OPENAI_SDK_AVAILABLE:
            latency_ms = int((time.monotonic() - started_at) * 1000)
            try:
                write_ai_usage_event(
                    user=request.user,
                    action="knowledge_ask",
                    endpoint=_request_path(request),
                    success=True,
                    status_code=200,
                    model_used="rule_engine",
                    test_type="knowledge",
                    module_id=None,
                    streamed=False,
                    latency_ms=latency_ms,
                    prompt_chars=len(q),
                    output_chars=0,
                    cases_count=0,
                    error_code="",
                    error_message="",
                    meta={"top_k": top_k, "category": category, "tag": tag},
                )
            except Exception:
                pass
            try:
                if slot:
                    release_ai_concurrency_slot(user_id=int(getattr(request.user, "id", 0) or 0))
            except Exception:
                pass
            answer = "未配置可用 AI 模型，已返回检索到的引用列表（citations）。"
            return Response(
                {
                    "success": True,
                    "question": q,
                    "answer_markdown": answer,
                    "citations": citations,
                    "engine": "search_only",
                    "top_k": top_k,
                }
            )

        ctx_text = "\n\n".join(ctx_blocks) if ctx_blocks else "（无可引用来源）"

        system_prompt = (
            "你是企业测试平台的知识库助手。你必须严格基于给定的引用来源回答问题，"
            "不得编造。回答中如果使用了来源信息，必须在句末标注引用编号，如 [C1]。"
            "若来源不足以回答，请说明缺失信息，并仍返回当前可引用的结论。"
        )
        user_msg = f"问题：{q}\n\n可引用来源：\n{ctx_text}"

        answer_md = ""
        err_msg = ""
        try:
            _debug_log_openai_target("ai_knowledge_ask", model_used, api_base_url)
            client = OpenAI(api_key=api_key, base_url=api_base_url, timeout=60.0)
            completion = client.chat.completions.create(
                model=model_used,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.2,
                max_tokens=1200,
            )
            answer_md = (completion.choices[0].message.content or "").strip()
        except Exception as exc:
            err_msg = str(exc)

        latency_ms = int((time.monotonic() - started_at) * 1000)
        try:
            write_ai_usage_event(
                user=request.user,
                action="knowledge_ask",
                endpoint=_request_path(request),
                success=bool(answer_md) and not err_msg,
                status_code=200 if (answer_md and not err_msg) else 502,
                model_used=str(model_used or ""),
                test_type="knowledge",
                module_id=None,
                streamed=False,
                latency_ms=latency_ms,
                prompt_chars=len(user_msg),
                output_chars=len(answer_md or ""),
                cases_count=0,
                error_code="" if not err_msg else "UPSTREAM",
                error_message=err_msg[:512] if err_msg else "",
                meta={"top_k": top_k, "category": category, "tag": tag, "citations": len(citations)},
            )
        except Exception:
            pass
        try:
            if slot:
                release_ai_concurrency_slot(user_id=int(getattr(request.user, "id", 0) or 0))
        except Exception:
            pass

        if err_msg or not answer_md:
            return Response(
                {
                    "success": False,
                    "message": err_msg or "生成失败",
                    "question": q,
                    "answer_markdown": "",
                    "citations": citations,
                },
                status=502,
            )

        return Response(
            {
                "success": True,
                "question": q,
                "answer_markdown": answer_md,
                "citations": citations,
                "model": model_used,
                "top_k": top_k,
            }
        )
