"""
Analysis Lab：报告详情聚合 + UI 执行失败 AI 诊断。
"""
from __future__ import annotations

import logging
import time
from urllib.parse import quote

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from assistant.models import UIScriptExecution
from assistant.services.analysis_lab_ui_report import depth_report_payload
from assistant.utils.script_runner import ScriptRunner

logger = logging.getLogger(__name__)


class AnalysisLabReportDetailsAPIView(APIView):
    """
    GET /api/reports/<id>/details/
    id 为 UIScriptExecution 主键（与指挥中心「执行」返回的 db id 一致）。
    """

    permission_classes = [IsAuthenticated]

    def get(self, request, pk: int):
        execution = (
            UIScriptExecution.objects.select_related("script")
            .filter(pk=int(pk))
            .first()
        )
        if execution is None:
            return Response({"detail": "报告/执行记录不存在"}, status=404)

        runner = ScriptRunner()
        # 报告页禁止全量拉取遥测，仅保留最近条目用于堆栈摘要
        logs = runner.get_execution_logs_tail(execution.execution_id, tail=50)

        payload = depth_report_payload(execution=execution, logs=logs, api_reports_id=int(pk))

        for step in payload.get("steps") or []:
            rel = step.get("relpath")
            if rel:
                step["screenshot_url"] = request.build_absolute_uri(
                    f"/api/assistant/ui-script-executions/{int(pk)}/evidence-image/?relpath={quote(str(rel))}"
                )

        return Response(payload)


class AiUiExecutionDiagnoseAPIView(APIView):
    """
    POST /api/ai/ui-execution-diagnose/
    body: { "stack_trace": str, "script_name"?: str }
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        from assistant.views import (
            OPENAI_SDK_AVAILABLE,
            _debug_log_openai_target,
            _get_active_ai_model_credentials,
            _guard_ai_request_or_429,
            _openai_missing_response_json,
            _request_path,
            release_ai_concurrency_slot,
            write_ai_usage_event,
        )

        started_at = time.monotonic()
        slot, denied = _guard_ai_request_or_429(request, action="ui_execution_diagnose")
        if denied is not None:
            return denied

        body = request.data if isinstance(request.data, dict) else {}
        stack = str(body.get("stack_trace") or body.get("error_text") or "").strip()
        script_name = str(body.get("script_name") or "").strip()

        if not stack:
            try:
                if slot:
                    release_ai_concurrency_slot(user_id=int(getattr(request.user, "id", 0) or 0))
            except Exception:
                pass
            return Response(
                {"success": False, "message": "stack_trace 不能为空", "suggestion": ""},
                status=400,
            )

        if not OPENAI_SDK_AVAILABLE:
            try:
                if slot:
                    release_ai_concurrency_slot(user_id=int(getattr(request.user, "id", 0) or 0))
            except Exception:
                pass
            return Response(
                {
                    "success": False,
                    "message": _openai_missing_response_json(),
                    "suggestion": "",
                },
                status=503,
            )

        api_key, api_base_url, model_used = _get_active_ai_model_credentials()
        if not api_key:
            try:
                if slot:
                    release_ai_concurrency_slot(user_id=int(getattr(request.user, "id", 0) or 0))
            except Exception:
                pass
            return Response(
                {
                    "success": False,
                    "message": "未配置可用 AI 模型，请在系统「模型接入」中连接后再试。",
                    "suggestion": "",
                },
                status=503,
            )

        from openai import OpenAI

        system_prompt = (
            "你是资深 UI 自动化（Selenium / Playwright）与 Python 测试工程师。"
            "根据用户提供的失败堆栈与遥测 stderr，用中文给出：1) 可能根因 2) 具体排查步骤 3) 可尝试的代码/配置修复。"
            "保持简洁，使用条目列表，不要编造日志中未出现的事实。"
        )
        user_msg = f"脚本：{script_name or '（未提供）'}\n\n错误与堆栈：\n{stack[:8000]}"

        suggestion = ""
        err_msg = ""
        try:
            _debug_log_openai_target("ui_execution_diagnose", model_used, api_base_url)
            client = OpenAI(api_key=api_key, base_url=api_base_url, timeout=55.0)
            completion = client.chat.completions.create(
                model=model_used,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.25,
                max_tokens=1200,
            )
            suggestion = (completion.choices[0].message.content or "").strip()
        except Exception as exc:
            err_msg = str(exc)
            logger.warning("ui_execution_diagnose LLM failed: %s", err_msg, exc_info=True)

        latency_ms = int((time.monotonic() - started_at) * 1000)
        try:
            write_ai_usage_event(
                user=request.user,
                action="ui_execution_diagnose",
                endpoint=_request_path(request),
                success=bool(suggestion) and not err_msg,
                status_code=200 if suggestion else 502,
                model_used=str(model_used or ""),
                test_type="ui",
                module_id=None,
                streamed=False,
                latency_ms=latency_ms,
                prompt_chars=len(user_msg),
                output_chars=len(suggestion or ""),
                cases_count=0,
                error_code="" if not err_msg else "UPSTREAM",
                error_message=err_msg[:512] if err_msg else "",
                meta={},
            )
        except Exception:
            pass
        try:
            if slot:
                release_ai_concurrency_slot(user_id=int(getattr(request.user, "id", 0) or 0))
        except Exception:
            pass

        if err_msg:
            return Response(
                {
                    "success": False,
                    "message": f"模型调用失败：{err_msg[:300]}",
                    "suggestion": "",
                },
                status=502,
            )

        return Response({"success": True, "message": "", "suggestion": suggestion})
