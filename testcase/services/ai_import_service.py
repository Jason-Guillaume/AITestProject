import logging
import time
from difflib import SequenceMatcher

from django.db import transaction
from rest_framework.exceptions import ValidationError

from testcase.models import (
    TEST_CASE_TYPE_API,
    TEST_CASE_TYPE_SECURITY,
    TestCase,
    TestCaseStep,
    TestModule,
)
from testcase.serialize import TestCaseSerializer
from testcase.services.ai_import_precheck_core import precheck_api_draft_item

logger = logging.getLogger(__name__)


class AiImportService:
    def __init__(self, user=None):
        self.user = user

    def run(
        self,
        project_id,
        test_type,
        items,
        run_id=None,
        default_module_id=None,
        strict=False,
        precheck_overrides=None,
        module_match_threshold=0.92,
        request=None,
    ):
        module_qs = TestModule.objects.filter(
            project_id=project_id, is_deleted=False, test_type=test_type
        )

        def _norm_module_key(name: str) -> str:
            return (name or "").strip().lower()

        module_names = list(module_qs.values_list("id", "name"))
        module_cache = {_norm_module_key(name): mid for (mid, name) in module_names}
        created_module_cache: dict[str, int] = {}

        def _best_module_match(name: str):
            raw = (name or "").strip()
            if not raw:
                return None, "", 0.0
            k = _norm_module_key(raw)
            if k in module_cache:
                return module_cache[k], raw, 1.0
            best = (None, "", 0.0)
            for mid, mname in module_names:
                try:
                    score = SequenceMatcher(None, raw, str(mname or "")).ratio()
                except Exception:
                    score = 0.0
                if score > best[2]:
                    best = (mid, str(mname or ""), float(score))
            if best[0] is not None and best[2] >= module_match_threshold:
                return best
            return None, best[1], best[2]

        def _get_or_create_module_id(module_name: str):
            raw = (module_name or "").strip()
            if not raw:
                return None
            k = _norm_module_key(raw)
            if k in created_module_cache:
                return created_module_cache[k], "created", raw, 1.0
            if k in module_cache:
                return module_cache[k], "exact", raw, 1.0

            matched_id, matched_name, score = _best_module_match(raw)
            if matched_id is not None:
                module_cache[k] = matched_id
                return matched_id, "fuzzy", matched_name, score

            m = TestModule.objects.create(
                project_id=project_id,
                name=raw,
                parent_id=None,
                test_type=test_type,
                creator=self.user if self._is_authenticated() else None,
                updater=self.user if self._is_authenticated() else None,
            )
            module_cache[k] = m.id
            created_module_cache[k] = m.id
            module_names.append((m.id, raw))
            return m.id, "created", raw, 1.0

        def _build_step_desc(row: dict) -> str:
            parts = []
            pre = str(row.get("precondition") or "").strip()
            if pre:
                parts.append(f"【前置条件】\n{pre}")
            steps = str(row.get("steps") or "").strip()
            if steps:
                parts.append(f"【操作步骤】\n{steps}")
            return "\n\n".join(parts) or "（无详细步骤，请编辑补充）"

        def _normalize_steps(row: dict):
            sl = row.get("steps_list")
            if sl is None:
                sl = row.get("stepsList")
            if sl is None and isinstance(row.get("steps"), list):
                sl = row.get("steps")
            if isinstance(sl, list) and sl:
                out = []
                for it in sl:
                    if not isinstance(it, dict):
                        continue
                    desc = str(
                        it.get("step_desc") or it.get("desc") or it.get("action") or ""
                    ).strip()
                    if not desc:
                        continue
                    exp = (
                        str(
                            it.get("expected_result") or it.get("expected") or ""
                        ).strip()
                        or "—"
                    )
                    out.append({"step_desc": desc, "expected_result": exp})
                if out:
                    return out
            exp = str(row.get("expected_result") or "").strip() or "—"
            return [{"step_desc": _build_step_desc(row), "expected_result": exp}]

        imported = []
        failed = []
        skipped = 0

        with transaction.atomic():
            for idx, raw in enumerate(items):
                sp = transaction.savepoint()
                try:
                    if not isinstance(raw, dict):
                        raise ValidationError("item 必须为对象")
                    case_name = str(raw.get("case_name") or "").strip()
                    if not case_name:
                        raise ValidationError("case_name 必填")
                    level = str(raw.get("level") or "").strip() or "P2"

                    module_name = str(
                        raw.get("module_name") or raw.get("moduleName") or ""
                    ).strip()
                    raw_mid = raw.get("module_id") or raw.get("moduleId")
                    mid = None
                    module_resolution = None
                    if raw_mid not in (None, ""):
                        try:
                            mid = int(raw_mid)
                        except (TypeError, ValueError):
                            mid = None
                        if mid is not None:
                            if not module_qs.filter(id=mid).exists():
                                raise ValidationError(
                                    "module_id 不存在或不属于当前项目/测试类型"
                                )
                            module_resolution = {
                                "mode": "explicit",
                                "matched_name": "",
                                "score": 1.0,
                            }
                    if mid is None:
                        resolved = (
                            _get_or_create_module_id(module_name)
                            if module_name
                            else None
                        )
                        mid = resolved[0] if resolved else None
                        module_resolution = (
                            {
                                "mode": resolved[1],
                                "matched_name": resolved[2],
                                "score": resolved[3],
                            }
                            if resolved
                            else None
                        )
                    if not mid and default_module_id:
                        mid = default_module_id
                    if not mid:
                        skipped += 1
                        raise ValidationError(
                            "缺少模块归属（module_name/default_module_id）"
                        )

                    payload: dict = {
                        "case_name": case_name,
                        "level": level,
                        "module": mid,
                        "test_type": test_type,
                        "ai_run": run_id,
                    }

                    if test_type == TEST_CASE_TYPE_API:
                        url = str(raw.get("api_url") or "").strip()
                        method = (
                            str(raw.get("api_method") or "GET").strip().upper()[:16]
                        )
                        if url:
                            payload["api_url"] = url
                        if method:
                            payload["api_method"] = method
                        if strict:
                            if not url:
                                raise ValidationError("API 用例缺少 api_url")
                            if not method:
                                raise ValidationError("API 用例缺少 api_method")
                            pr = precheck_api_draft_item(raw, precheck_overrides)
                            if not pr.get("ok"):
                                msg_parts = []
                                if pr.get("error"):
                                    msg_parts.append(str(pr["error"]))
                                uv = pr.get("unresolved_vars") or []
                                if uv:
                                    msg_parts.append(
                                        "未替换变量: "
                                        + ", ".join(str(x) for x in uv[:20])
                                    )
                                raise ValidationError(
                                    "; ".join(msg_parts) or "API 导入前预检未通过"
                                )
                        if isinstance(raw.get("api_headers"), dict):
                            payload["api_headers"] = raw.get("api_headers")
                        if raw.get("api_body") is not None:
                            payload["api_body"] = raw.get("api_body")
                        if raw.get("api_expected_status") not in (None, ""):
                            try:
                                payload["api_expected_status"] = int(
                                    raw.get("api_expected_status")
                                )
                            except (TypeError, ValueError):
                                pass
                        if raw.get("api_source_curl"):
                            payload["api_source_curl"] = str(
                                raw.get("api_source_curl") or ""
                            )[:2000]

                    if test_type == TEST_CASE_TYPE_SECURITY:
                        if raw.get("attack_surface"):
                            payload["attack_surface"] = str(
                                raw.get("attack_surface") or ""
                            )[:512]
                        if raw.get("tool_preset"):
                            payload["tool_preset"] = str(raw.get("tool_preset") or "")[
                                :128
                            ]
                        rl = str(raw.get("risk_level") or "").strip()
                        if rl in ("高", "中", "低"):
                            payload["risk_level"] = rl

                    serializer = TestCaseSerializer(
                        data=payload, context={"request": request}
                    )
                    try:
                        serializer.is_valid(raise_exception=True)
                    except ValidationError as exc:
                        detail = getattr(exc, "detail", None)
                        code = None
                        if isinstance(detail, dict):
                            raw_code = detail.get("code")
                            if isinstance(raw_code, list) and raw_code:
                                code = str(raw_code[0])
                            elif raw_code is not None:
                                code = str(raw_code)
                        if code == "RECYCLE_CONFLICT":
                            base = case_name or "用例"
                            suffix = f"·{int(time.time())}"
                            next_name = (base + suffix)[:255]
                            payload["case_name"] = next_name
                            serializer = TestCaseSerializer(
                                data=payload, context={"request": request}
                            )
                            serializer.is_valid(raise_exception=True)
                        else:
                            raise
                    case_obj = serializer.save()

                    steps = _normalize_steps(raw)
                    if strict and not steps:
                        raise ValidationError("用例缺少可导入的步骤")
                    for sidx, st in enumerate(steps, start=1):
                        TestCaseStep.objects.create(
                            testcase_id=case_obj.id,
                            step_number=sidx,
                            step_desc=str(st.get("step_desc") or "").strip()[:4000]
                            or "（无详细步骤，请编辑补充）",
                            expected_result=str(
                                st.get("expected_result") or ""
                            ).strip()[:2000]
                            or "—",
                            creator=(
                                self.user if self._is_authenticated() else None
                            ),
                            updater=(
                                self.user if self._is_authenticated() else None
                            ),
                        )

                    imported.append(
                        {
                            "index": idx,
                            "case_id": case_obj.id,
                            "case_name": case_obj.case_name,
                            "steps_created": len(steps),
                            "module_resolution": module_resolution,
                        }
                    )
                    transaction.savepoint_commit(sp)
                except Exception as e:
                    transaction.savepoint_rollback(sp)
                    failed.append({"index": idx, "error": str(e)})

        return {
            "imported": imported,
            "failed": failed,
            "skipped": skipped,
        }

    def _is_authenticated(self):
        return getattr(self.user, "is_authenticated", False)
