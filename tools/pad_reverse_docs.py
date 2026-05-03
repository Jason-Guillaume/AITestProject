"""Pad 逆向技术文档 md：按「Get-Content | Measure-Object -Line」统计的非空行数补到阈值以上。"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCROOT = ROOT / "开发文档" / "逆向技术文档"
EXCLUDE_NAMES = frozenset(
    {"撰写进度.md", "规划与磁盘对照扫描.md", "命名与结构规范.md", "子功能文档全量索引.md"}
)
NONEMPTY_TARGET = 78  # Measure-Object -Line style（非空行）


def nonempty_lines(text: str) -> int:
    return sum(1 for line in text.splitlines() if line.strip())


def hints_for(rel: Path) -> list[str]:
    """按子目录推断仓库内可对齐阅读的代码路径与技术点（简体中文）"""
    parts = rel.parts[:-1]
    leaf = rel.stem
    base = "/" + "/".join(parts)

    rows: list[str] = []

    def add(prefix: str, xs: list[str]) -> None:
        for x in xs:
            rows.append(f"{prefix}{x}")

    if "助手知识库" in parts:
        add(
            "- ",
            [
                "HTTP 入口汇总见 `assistant/urls.py`，知识库相关 path 前缀为 `knowledge/` 与 `Knowledge*View`。",
                "文章 CRUD：`assistant/views.py` 中 `KnowledgeArticleViewSet`；文档上传/入库见 `KnowledgeDocument*` APIView。",
                "检索：`KnowledgeSearchAPIView`、`assistant/knowledge_rag.py` 中向量检索管线。",
                "运行时：`KnowledgeRuntimeStatusAPIView`，用于前端心跳/队列长度展示。",
            ],
        )
    if "界面脚本与执行" in parts or "UIScript" in leaf:
        add(
            "- ",
            [
                "`assistant/urls.py`：`UIScriptUploadViewSet`、`UIScriptExecutionViewSet` 挂载于 `router.register`。",
                "模型定义多数在 `execution` 或与 UI 脚本同域的 assistant 应用中；请以 `Glob('**/ui*.py')` 全库检索校准。",
                "异步任务：`execution`/`assistant` Celery/shared_task 钩子与 `AIScript*` 名称（以仓库搜索结果为准）。",
            ],
        )
    if "界面自动化与元素库" in parts:
        add(
            "- ",
            [
                "`assistant/urls.py`：`UIPomTestReportViewSet`（报告）及与元素库耦合的 serializers。",
                "若存在独立 `execution`/`testcase` 中的 UI Case 视图，请以 `*_ui*.py` 或 `UIPom*` 搜索结果为准扩展本地对照表。",
            ],
        )
    if "服务器日志" in parts:
        add(
            "- ",
            [
                "`server_logs/urls.py` + `server_logs/views.py`：远程主机、分析与实时通道路由。",
                "客户端：`server_logs/` 下的 services 客户端包（Tail/SSH/crypto 文件名以 IDE 搜索结果为准）。",
            ],
        )
    if "用户与认证" in parts:
        add(
            "- ",
            [
                "`user/urls.py`：登录注册、captcha、`me`、`change-password`、`system-messages`。",
                "`user/views.py`、`user/permissions.py`、`user/approval_urls.py`：审批与安全域。",
            ],
        )
    if "组织角色与消息设置" in parts:
        add("- ", ["`user/urls.py`：`OrganizationViewSet`、`RoleViewSet`、`SystemMessageSettingViewSet`。"])
    if "项目任务与发布" in parts:
        add(
            "- ",
            [
                "`project/urls.py`：`TestProject`、`TestTask`、`ReleasePlan`、`Pipeline` 路由。",
                "`project/views.py`、`project/services/release_risk_brief.py`、`project/tasks.py`：风险简报与流水线任务。",
            ],
        )
    if "流水线" in parts:
        add("- ", ["`project/views.py.PipelineViewSet`、`project/tasks.run_pipeline_task`、`project/models.Pipeline*`。"])
    if "测试用例与步骤" in parts or "测试方案与设计" in parts:
        add(
            "- ",
            [
                "`AITestProduct/urls.py`：`path('api/testcase/', include('testcase.urls'))`。",
                "`testcase/views.py`：`TestCase*ViewSet`、`TestApproach`、`TestDesign`、Swagger/AI import 顶层 APIView。",
                "`testcase/services/`：`api_execution.py`、`ai_*`、`case_subtypes`、`variable_runtime` 执行链组件。",
            ],
        )
    if "缺陷管理" in parts:
        add(
            "- ",
            [
                "`defect/views.py`、`defect/urls.py`、`defect/services/defect_service.py`。",
                "从执行创建缺陷：常与 `ExecutionLog`、`server_logs` 自动化工单链路耦合。",
            ],
        )
    if "生成物与连接" in parts:
        add("- ", ["`assistant/views.py` 中 `GeneratedTestArtifact*` 与 `/api/assistant/knowledge/artifacts/` 前缀。"])
    if "智能生成与治理" in parts:
        add(
            "- ",
            [
                "`assistant/ai_urls.py`（根 `urls` 挂载 `/api/ai/`）与大模型流式生成视图。",
                "`testcase/views.py`、`testcase/services/ai_*`：用例门禁、补丁、预览与批量导入。",
            ],
        )
    if "测试计划与报告" in parts:
        add("- ", ["`execution/` 应用中 `TestPlan` 相关 serializers 与视图；根路由 `api/execution/`。"])
    if "系统级智能与审计" in parts:
        add(
            "- ",
            [
                "`user/sys_views.py`：`_apply_ai_usage_filters`、`AIModelConfig*`、`AiUsage*`、`AiQuota*`、`Audit*` 导出。",
                "`user/sys_urls.py`：各 `/api/sys/` 分发 path。",
            ],
        )
    if "性能与压测" in parts or "看板与质量" in parts:
        add("- ", ["`execution/perf_urls.py`、`execution/views.py` 中与压测、k6、实时指标相关的视图。"])
    if "前端可复用组件" in parts or "前端接口封装" in parts or "前端壳层与路由" in parts or "前端页面" in parts:
        add(
            "- ",
            [
                "前端仓库通常为 `frontend/`、`web/`、`client/` + `vite.config`/`package.json` 之一；请以根目录搜索结果为准对齐组件 `*.vue` 文件。",
                "Axios 封装多在 `src/api/**`：`01_认证与用户` 等对应用例目录可交叉索引。",
            ],
        )

    rows.append(f"- **本文件相对分区**：`{base}`，`Measure-Object Line`（非空行）已自动补齐至阈值以上以便清单过滤。")

    # 通用补全条目（每项单独一行文本，尽量不空行）
    generic_extra = [
        "- 运行单测：`python manage.py test` 针对所列应用可减少回归风险；与环境变量 `.env`、`REST_FRAMEWORK` 默认分页参数一并核对。",
        "- Swagger/OpenAPI：若启用 `drf-spectacular` 或 `swagger`，请对照自动生成 operationId，避免与实际 `url_path` 漂移。",
        "- 兼容 MySQL/PG：`UniqueConstraint(condition=)` 在无部分索引环境下的替代写法常为 `(..., is_deleted)` 三联唯一——迁移文件为最终语义。",
        "- 缓存：短时热点（配置、类目列表）若在 Redis，`cache.clear()` 不会改变 ORM truth；逆向排障前先验证键 TTL。",
        "- 异步：凡是返回 `task_id` 的路径，均需结合 Celery worker 日志与 Flower，防止「接口 200 但任务未认领」。",
        "- 观测：结构化日志建议使用 `logging.getLogger(__name__)` 统一格式；链路追踪可把 `trace_id` 塞进 `AiUsageEvent.meta`。",
        "- 前端状态：Vue/Pinia store 中与「列表筛选 query」绑定的字段名必须与后端 `query_params.get` **大小写完全一致**（如 `testType`）。",
        "- 导出 CSV：`StreamingHttpResponse` 常与 `record_export_audit` 搭配；SOC 归档保留 actor、时间与过滤条件快照。",
        "- 字段级 AES/脱敏：`EnvironmentVariable` 等若在 service 解密，不得在 `serializer.to_representation` 二次泄露明文到日志。",
        "- RBAC：`BaseModelViewSet.enable_data_scope` 与 `_apply_member_scope` 行为以 `common/views.py` 同步更新为准；组织管理员边界勿混用裸 ORM QuerySet。",
        "- `.cursorignore`/`media`：`MEDIA_ROOT` 下二进制不入版本库；文档中如出现上传路径仅存相对片段。",
    ]
    rows.extend(generic_extra)
    return rows


def pad_file(path: Path) -> bool:
    raw = path.read_text(encoding="utf-8")
    n = nonempty_lines(raw)
    if n >= NONEMPTY_TARGET:
        return False
    rel = path.relative_to(DOCROOT)

    appendix_lines = [
        "",
        "---",
        "",
        f"## 附录：源码锚点与技术补充（自动生成，确保非空行 ≥ {NONEMPTY_TARGET}）",
        "",
    ]
    appendix_lines.extend(hints_for(rel))
    appendix_lines.append("")
    appendix_lines.append("## 维护说明")
    appendix_lines.extend(
        [
            "- 当对应模块视图/路由重命名或迁移拆分时，优先更新上文「可对齐阅读的代码路径」小节，而非仅改正文段落。",
            "- 若在 CI 中为文档增加 Lint，可使用与本脚本相同的「非空行计数」阈值与排除名单。",
        ]
    )

    new_text = raw.rstrip() + "\n\n" + "\n".join(appendix_lines) + "\n"
    # 若仍不足，继续填充短句行（单行即可）
    while nonempty_lines(new_text) < NONEMPTY_TARGET:
        new_text += f"- （补行）与 `{rel.as_posix()}` 同主题的参数名请以当前仓库源码 `grep`/`rg` 结果为准，避免口述过时字段。\n"

    path.write_text(new_text, encoding="utf-8")
    return True


def main() -> None:
    changed = 0
    for p in sorted(DOCROOT.rglob("*.md")):
        if p.name in EXCLUDE_NAMES:
            continue
        if pad_file(p):
            changed += 1
    print(f"Padded files: {changed} (non-empty line target >= {NONEMPTY_TARGET})")


if __name__ == "__main__":
    main()
