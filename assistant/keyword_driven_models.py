"""
关键字驱动框架 (Keyword-Driven Framework) 核心模型

与旧 POM 模型 (ui_element_models.py) 的关键区别：
  - KWElementLocator 独立于页面层级，作为全局资源复用
  - KWTestCase 直接挂项目，消除 module → page 层级依赖
  - KWActionStep 通过 FK 引用独立定位器，解决硬编码和无复用问题
  - action_value / test_data 分离，支持参数化驱动

类名加 KW 前缀，避免与 ui_element_models 中的同名模型冲突。
"""
from django.db import models
from common.models import BaseModel


class KWElementLocator(BaseModel):
    """
    关键字驱动 - UI 元素定位器（独立元素库）

    定位器与页面/模块解耦，作为独立资源存在。
    多个 Step 可引用同一个 Locator，UI 变更时只改一处。
    """

    LOCATOR_ID = "id"
    LOCATOR_NAME = "name"
    LOCATOR_XPATH = "xpath"
    LOCATOR_CSS_SELECTOR = "css_selector"
    LOCATOR_CLASS_NAME = "class_name"
    LOCATOR_TAG_NAME = "tag_name"
    LOCATOR_LINK_TEXT = "link_text"
    LOCATOR_PARTIAL_LINK_TEXT = "partial_link_text"

    LOCATOR_TYPE_CHOICES = [
        (LOCATOR_ID, "ID"),
        (LOCATOR_NAME, "Name"),
        (LOCATOR_XPATH, "XPath"),
        (LOCATOR_CSS_SELECTOR, "CSS Selector"),
        (LOCATOR_CLASS_NAME, "Class Name"),
        (LOCATOR_TAG_NAME, "Tag Name"),
        (LOCATOR_LINK_TEXT, "Link Text"),
        (LOCATOR_PARTIAL_LINK_TEXT, "Partial Link Text"),
    ]

    SELENIUM_BY_MAP = {
        LOCATOR_ID: "By.ID",
        LOCATOR_NAME: "By.NAME",
        LOCATOR_XPATH: "By.XPATH",
        LOCATOR_CSS_SELECTOR: "By.CSS_SELECTOR",
        LOCATOR_CLASS_NAME: "By.CLASS_NAME",
        LOCATOR_TAG_NAME: "By.TAG_NAME",
        LOCATOR_LINK_TEXT: "By.LINK_TEXT",
        LOCATOR_PARTIAL_LINK_TEXT: "By.PARTIAL_LINK_TEXT",
    }

    project = models.ForeignKey(
        "project.TestProject",
        on_delete=models.CASCADE,
        related_name="kw_element_locators",
        verbose_name="所属项目",
    )
    name = models.CharField(
        max_length=255,
        verbose_name="元素名称",
    )
    locator_type = models.CharField(
        max_length=32,
        choices=LOCATOR_TYPE_CHOICES,
        default=LOCATOR_XPATH,
        verbose_name="定位方式",
    )
    locator_expression = models.CharField(
        max_length=255,
        verbose_name="定位表达式",
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="描述",
    )

    class Meta:
        db_table = "kw_ui_element_locator"
        ordering = ["id"]
        verbose_name = "UI元素定位器(KW)"
        verbose_name_plural = "UI元素定位器(KW)"
        indexes = [
            models.Index(fields=["project", "locator_type"], name="idx_kw_loc_proj_type"),
            models.Index(fields=["name"], name="idx_kw_loc_name"),
        ]
        unique_together = [("project", "name")]

    def __str__(self):
        return f"[{self.get_locator_type_display()}] {self.name}"

    def to_executor_dict(self):
        return {
            "id": self.pk,
            "name": self.name,
            "by": self.SELENIUM_BY_MAP.get(self.locator_type, "By.XPATH"),
            "locator_type": self.locator_type,
            "expression": self.locator_expression,
        }


class KWTestCase(BaseModel):
    """
    关键字驱动 - 测试用例

    一个 Case 由有序的 KWActionStep 列表组成。
    直接挂项目，与旧 POM 的 module → page 层级解耦。
    """

    STATUS_DRAFT = "draft"
    STATUS_READY = "ready"
    STATUS_DEPRECATED = "deprecated"

    STATUS_CHOICES = [
        (STATUS_DRAFT, "草稿"),
        (STATUS_READY, "就绪"),
        (STATUS_DEPRECATED, "已废弃"),
    ]

    project = models.ForeignKey(
        "project.TestProject",
        on_delete=models.CASCADE,
        related_name="kw_test_cases",
        verbose_name="所属项目",
    )
    name = models.CharField(
        max_length=255,
        verbose_name="用例名称",
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="用例描述",
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        verbose_name="用例状态",
    )
    base_url = models.URLField(
        max_length=512,
        blank=True,
        default="",
        verbose_name="基础URL",
    )
    variables = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="用例级变量",
    )
    timeout_seconds = models.PositiveIntegerField(
        default=300,
        verbose_name="超时时间(秒)",
    )

    class Meta:
        db_table = "kw_ui_test_case"
        ordering = ["id"]
        verbose_name = "关键字驱动用例"
        verbose_name_plural = "关键字驱动用例"
        indexes = [
            models.Index(fields=["project", "status"], name="idx_kw_tc_proj_status"),
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

    def to_executor_dict(self):
        steps = self.steps.select_related("element").order_by("step_order")
        return {
            "id": self.pk,
            "name": self.name,
            "base_url": self.base_url,
            "variables": self.variables,
            "timeout_seconds": self.timeout_seconds,
            "steps": [step.to_executor_dict() for step in steps],
        }


class KWActionStep(BaseModel):
    """
    关键字驱动 - 执行步骤

    每一行 = 一个关键字操作。
    element FK 引用独立定位器，解决硬编码和无复用。
    action_value 存放操作语义值，test_data 存放结构化测试数据。
    """

    ACTION_CLICK = "click"
    ACTION_INPUT = "input"
    ACTION_ASSERT = "assert"
    ACTION_HOVER = "hover"
    ACTION_SELECT = "select"
    ACTION_WAIT = "wait"
    ACTION_SLEEP = "sleep"
    ACTION_NAVIGATE = "navigate"
    ACTION_SWITCH_WINDOW = "switch_window"
    ACTION_SWITCH_FRAME = "switch_frame"
    ACTION_SCROLL = "scroll"
    ACTION_EXECUTE_JS = "execute_js"

    ACTION_TYPE_CHOICES = [
        (ACTION_CLICK, "点击"),
        (ACTION_INPUT, "输入"),
        (ACTION_ASSERT, "断言"),
        (ACTION_HOVER, "悬停"),
        (ACTION_SELECT, "选择"),
        (ACTION_WAIT, "等待元素"),
        (ACTION_SLEEP, "休眠"),
        (ACTION_NAVIGATE, "导航"),
        (ACTION_SWITCH_WINDOW, "切换窗口"),
        (ACTION_SWITCH_FRAME, "切换Frame"),
        (ACTION_SCROLL, "滚动"),
        (ACTION_EXECUTE_JS, "执行JS"),
    ]

    ASSERT_VISIBLE = "visible"
    ASSERT_NOT_VISIBLE = "not_visible"
    ASSERT_TEXT_EQUALS = "text_equals"
    ASSERT_TEXT_CONTAINS = "text_contains"
    ASSERT_ATTRIBUTE_EQUALS = "attribute_equals"
    ASSERT_URL_CONTAINS = "url_contains"
    ASSERT_TITLE_CONTAINS = "title_contains"
    ASSERT_ELEMENT_COUNT = "element_count"

    ASSERT_TYPE_CHOICES = [
        (ASSERT_VISIBLE, "元素可见"),
        (ASSERT_NOT_VISIBLE, "元素不可见"),
        (ASSERT_TEXT_EQUALS, "文本相等"),
        (ASSERT_TEXT_CONTAINS, "文本包含"),
        (ASSERT_ATTRIBUTE_EQUALS, "属性相等"),
        (ASSERT_URL_CONTAINS, "URL包含"),
        (ASSERT_TITLE_CONTAINS, "标题包含"),
        (ASSERT_ELEMENT_COUNT, "元素数量"),
    ]

    ELEMENT_REQUIRED_ACTIONS = {
        ACTION_CLICK, ACTION_INPUT, ACTION_HOVER,
        ACTION_SELECT, ACTION_WAIT, ACTION_SCROLL,
    }

    test_case = models.ForeignKey(
        KWTestCase,
        on_delete=models.CASCADE,
        related_name="steps",
        verbose_name="所属测试用例",
    )
    step_order = models.PositiveIntegerField(
        verbose_name="步骤序号",
    )
    action_type = models.CharField(
        max_length=32,
        choices=ACTION_TYPE_CHOICES,
        verbose_name="操作类型",
    )
    element = models.ForeignKey(
        KWElementLocator,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="referencing_steps",
        verbose_name="关联元素",
    )
    action_value = models.TextField(
        blank=True,
        default="",
        verbose_name="操作值",
    )
    assert_type = models.CharField(
        max_length=32,
        blank=True,
        default="",
        choices=ASSERT_TYPE_CHOICES,
        verbose_name="断言类型",
    )
    assert_expected = models.TextField(
        blank=True,
        default="",
        verbose_name="断言期望值",
    )
    test_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="测试数据",
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="步骤描述",
    )
    enabled = models.BooleanField(
        default=True,
        verbose_name="是否启用",
    )

    class Meta:
        db_table = "kw_ui_action_step"
        ordering = ["step_order"]
        verbose_name = "关键字驱动步骤"
        verbose_name_plural = "关键字驱动步骤"
        indexes = [
            models.Index(fields=["test_case", "step_order"], name="idx_kw_step_case_order"),
        ]
        unique_together = [("test_case", "step_order")]

    def __str__(self):
        locator_hint = f" → {self.element.name}" if self.element else ""
        return f"Step {self.step_order}: {self.get_action_type_display()}{locator_hint}"

    def to_executor_dict(self):
        result = {
            "step": self.step_order,
            "action": self.action_type,
            "action_label": self.get_action_type_display(),
            "element_id": self.element_id,
            "locator": self.element.to_executor_dict() if self.element else None,
            "value": self.action_value,
            "test_data": self.test_data,
            "enabled": self.enabled,
            "description": self.description,
        }
        if self.action_type == self.ACTION_ASSERT:
            result["assert_type"] = self.assert_type
            result["expected"] = self.assert_expected
        return result
