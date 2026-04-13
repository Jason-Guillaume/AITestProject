"""
用例子类型（多表继承）读写辅助：View / Serializer 复用，避免散落 try/except。
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple, Type

from django.core.exceptions import ObjectDoesNotExist
from django.db import models

from testcase.models import (
    TEST_CASE_TYPE_API,
    TEST_CASE_TYPE_PERFORMANCE,
    TEST_CASE_TYPE_SECURITY,
    TEST_CASE_TYPE_UI_AUTOMATION,
    ApiTestCase,
    PerfTestCase,
    SecurityTestCase,
    TestCase,
    UITestCase,
)

API_FIELD_KEYS = (
    "api_url",
    "api_method",
    "api_headers",
    "api_body",
    "api_expected_status",
    "api_source_curl",
)
PERF_FIELD_KEYS = ("concurrency", "duration_seconds", "target_rps")
SECURITY_FIELD_KEYS = ("attack_surface", "tool_preset", "risk_level")
UI_FIELD_KEYS = ("app_under_test", "primary_locator", "automation_framework")

API_DEFAULTS: Dict[str, Any] = {
    "api_url": "",
    "api_method": "GET",
    "api_headers": {},
    "api_body": {},
    "api_expected_status": None,
    "api_source_curl": "",
}
PERF_DEFAULTS = {"concurrency": 1, "duration_seconds": 60, "target_rps": None}
SECURITY_DEFAULTS = {"attack_surface": "", "tool_preset": "", "risk_level": ""}
UI_DEFAULTS = {
    "app_under_test": "",
    "primary_locator": "",
    "automation_framework": "",
}


def split_typed_payload_create(
    validated_data: dict, initial_data: Optional[dict]
) -> Tuple[dict, dict, dict, dict]:
    """创建：子类字段从 validated_data 拆出并补默认。"""
    initial_data = initial_data or {}

    def take(keys: Tuple[str, ...], defaults: Dict[str, Any]) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for k in keys:
            if k in validated_data:
                out[k] = validated_data.pop(k)
            elif k in initial_data:
                out[k] = initial_data[k]
            elif k in defaults:
                out[k] = defaults[k]
        return out

    return (
        take(API_FIELD_KEYS, API_DEFAULTS),
        take(PERF_FIELD_KEYS, PERF_DEFAULTS),
        take(SECURITY_FIELD_KEYS, SECURITY_DEFAULTS),
        take(UI_FIELD_KEYS, UI_DEFAULTS),
    )


def split_typed_payload_update(validated_data: dict) -> Tuple[dict, dict, dict, dict]:
    """更新：仅处理请求体里显式出现的子类字段。"""

    def pick(keys: Tuple[str, ...]) -> Dict[str, Any]:
        return {k: validated_data.pop(k) for k in keys if k in validated_data}

    return (
        pick(API_FIELD_KEYS),
        pick(PERF_FIELD_KEYS),
        pick(SECURITY_FIELD_KEYS),
        pick(UI_FIELD_KEYS),
    )


def inject_typed_read_representation(instance: TestCase, data: dict) -> None:
    """列表/详情 JSON 扁平化：把子表字段写入 data。"""
    tt = (instance.test_type or "").strip()
    if tt == TEST_CASE_TYPE_API:
        try:
            a = instance.apitestcase
            data["api_url"] = a.api_url
            data["api_method"] = a.api_method
            data["api_headers"] = a.api_headers
            data["api_body"] = a.api_body
            data["api_expected_status"] = a.api_expected_status
            data["api_source_curl"] = getattr(a, "api_source_curl", "") or ""
        except ObjectDoesNotExist:
            for k, v in API_DEFAULTS.items():
                data[k] = v
    else:
        for k, v in API_DEFAULTS.items():
            data[k] = v

    if tt == TEST_CASE_TYPE_PERFORMANCE:
        try:
            p = instance.perftestcase
            data["concurrency"] = p.concurrency
            data["duration_seconds"] = p.duration_seconds
            data["target_rps"] = p.target_rps
        except ObjectDoesNotExist:
            for k, v in PERF_DEFAULTS.items():
                data[k] = v
    else:
        for k, v in PERF_DEFAULTS.items():
            data[k] = v

    if tt == TEST_CASE_TYPE_SECURITY:
        try:
            s = instance.securitytestcase
            data["attack_surface"] = s.attack_surface
            data["tool_preset"] = s.tool_preset
            data["risk_level"] = getattr(s, "risk_level", "") or ""
        except ObjectDoesNotExist:
            for k, v in SECURITY_DEFAULTS.items():
                data[k] = v
    else:
        for k, v in SECURITY_DEFAULTS.items():
            data[k] = v

    if tt == TEST_CASE_TYPE_UI_AUTOMATION:
        try:
            u = instance.uitestcase
            data["app_under_test"] = u.app_under_test
            data["primary_locator"] = u.primary_locator
            data["automation_framework"] = u.automation_framework
        except ObjectDoesNotExist:
            for k, v in UI_DEFAULTS.items():
                data[k] = v
    else:
        for k, v in UI_DEFAULTS.items():
            data[k] = v


def _merge_child(
    model: Type[models.Model],
    instance: TestCase,
    payload: Dict[str, Any],
    defaults: Dict[str, Any],
    *,
    partial: bool,
) -> None:
    if partial and not payload:
        return
    try:
        obj = model.objects.get(pk=instance.pk)
    except model.DoesNotExist:
        merged = defaults.copy()
        merged.update(payload)
        model.objects.create(testcase_ptr=instance, **merged)
        return
    for k, v in payload.items():
        setattr(obj, k, v)
    obj.save()


def sync_typed_children(
    instance: TestCase,
    test_type: str,
    api: Dict[str, Any],
    perf: Dict[str, Any],
    sec: Dict[str, Any],
    ui: Dict[str, Any],
    *,
    partial: bool = False,
) -> None:
    """创建或更新与 test_type 对应的子表行（partial 时仅写入出现的字段）。"""
    if test_type == TEST_CASE_TYPE_API:
        _merge_child(ApiTestCase, instance, api, API_DEFAULTS, partial=partial)
    if test_type == TEST_CASE_TYPE_PERFORMANCE:
        _merge_child(PerfTestCase, instance, perf, PERF_DEFAULTS, partial=partial)
    if test_type == TEST_CASE_TYPE_SECURITY:
        _merge_child(SecurityTestCase, instance, sec, SECURITY_DEFAULTS, partial=partial)
    if test_type == TEST_CASE_TYPE_UI_AUTOMATION:
        _merge_child(UITestCase, instance, ui, UI_DEFAULTS, partial=partial)


def create_typed_case(
    test_type: str, base_data: dict, api: dict, perf: dict, sec: dict, ui: dict
) -> TestCase:
    if test_type == TEST_CASE_TYPE_API:
        return ApiTestCase.objects.create(**base_data, **api)
    if test_type == TEST_CASE_TYPE_PERFORMANCE:
        return PerfTestCase.objects.create(**base_data, **perf)
    if test_type == TEST_CASE_TYPE_SECURITY:
        return SecurityTestCase.objects.create(**base_data, **sec)
    if test_type == TEST_CASE_TYPE_UI_AUTOMATION:
        return UITestCase.objects.create(**base_data, **ui)
    return TestCase.objects.create(**base_data)


def get_api_profile_for_execute(case: TestCase) -> Optional[ApiTestCase]:
    if case.test_type != TEST_CASE_TYPE_API:
        return None
    try:
        return case.apitestcase
    except ObjectDoesNotExist:
        return None
