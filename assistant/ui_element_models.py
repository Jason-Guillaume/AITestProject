"""
UI自动化元素库模型 - 基于Page Object Model (POM)架构
"""
from django.db import models
from common.models import BaseModel


class UIModule(BaseModel):
    """
    UI模块管理 - POM架构的第一层
    支持树形结构，可以创建嵌套的子模块
    """
    project = models.ForeignKey(
        "project.TestProject",
        on_delete=models.CASCADE,
        related_name="ui_modules",
        verbose_name="所属项目"
    )
    name = models.CharField(
        max_length=255,
        verbose_name="模块名称"
    )
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="children",
        verbose_name="父模块"
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="模块描述"
    )
    order = models.IntegerField(
        default=0,
        verbose_name="排序序号"
    )

    class Meta:
        db_table = "ui_module"
        ordering = ["order", "id"]
        verbose_name = "UI模块"
        verbose_name_plural = "UI模块"
        indexes = [
            models.Index(fields=["project", "parent"]),
        ]

    def __str__(self):
        return f"{self.project.name} - {self.name}"


class UIPage(BaseModel):
    """
    UI页面管理 - POM架构的第二层
    每个页面属于一个模块，包含多个页面元素
    """
    module = models.ForeignKey(
        UIModule,
        on_delete=models.CASCADE,
        related_name="pages",
        verbose_name="所属模块"
    )
    name = models.CharField(
        max_length=255,
        verbose_name="页面名称"
    )
    url = models.CharField(
        max_length=512,
        blank=True,
        default="",
        verbose_name="页面URL"
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="页面描述"
    )
    order = models.IntegerField(
        default=0,
        verbose_name="排序序号"
    )

    class Meta:
        db_table = "ui_page"
        ordering = ["order", "id"]
        verbose_name = "UI页面"
        verbose_name_plural = "UI页面"
        indexes = [
            models.Index(fields=["module", "order"]),
        ]

    def __str__(self):
        return f"{self.module.name} - {self.name}"


class UIPageElement(BaseModel):
    """
    UI页面元素 - POM架构的第三层（元素库）
    存储页面元素的定位信息
    """
    LOCATOR_ID = "id"
    LOCATOR_NAME = "name"
    LOCATOR_XPATH = "xpath"
    LOCATOR_CSS = "css"
    LOCATOR_CLASS = "class"
    LOCATOR_TAG = "tag"
    LOCATOR_LINK_TEXT = "link_text"
    LOCATOR_PARTIAL_LINK_TEXT = "partial_link_text"

    LOCATOR_TYPE_CHOICES = [
        (LOCATOR_ID, "ID"),
        (LOCATOR_NAME, "Name"),
        (LOCATOR_XPATH, "XPath"),
        (LOCATOR_CSS, "CSS Selector"),
        (LOCATOR_CLASS, "Class Name"),
        (LOCATOR_TAG, "Tag Name"),
        (LOCATOR_LINK_TEXT, "Link Text"),
        (LOCATOR_PARTIAL_LINK_TEXT, "Partial Link Text"),
    ]

    page = models.ForeignKey(
        UIPage,
        on_delete=models.CASCADE,
        related_name="elements",
        verbose_name="所属页面"
    )
    name = models.CharField(
        max_length=255,
        verbose_name="元素名称"
    )
    locator_type = models.CharField(
        max_length=32,
        choices=LOCATOR_TYPE_CHOICES,
        default=LOCATOR_XPATH,
        verbose_name="定位方式"
    )
    locator_value = models.TextField(
        verbose_name="定位表达式"
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="元素描述"
    )
    order = models.IntegerField(
        default=0,
        verbose_name="排序序号"
    )

    class Meta:
        db_table = "ui_page_element"
        ordering = ["order", "id"]
        verbose_name = "UI页面元素"
        verbose_name_plural = "UI页面元素"
        indexes = [
            models.Index(fields=["page", "order"]),
            models.Index(fields=["name"]),
        ]

    def __str__(self):
        return f"{self.page.name} - {self.name}"


class UITestCase(BaseModel):
    """
    UI测试用例 - POM架构的测试用例层
    """
    module = models.ForeignKey(
        UIModule,
        on_delete=models.CASCADE,
        related_name="test_cases",
        verbose_name="所属模块"
    )
    name = models.CharField(
        max_length=255,
        verbose_name="用例名称"
    )
    preconditions = models.TextField(
        blank=True,
        default="",
        verbose_name="前置条件"
    )
    expected_result = models.TextField(
        blank=True,
        default="",
        verbose_name="预期结果"
    )
    priority = models.IntegerField(
        default=2,
        verbose_name="优先级"
    )
    order = models.IntegerField(
        default=0,
        verbose_name="排序序号"
    )

    class Meta:
        db_table = "ui_test_case"
        ordering = ["order", "id"]
        verbose_name = "UI测试用例"
        verbose_name_plural = "UI测试用例"
        indexes = [
            models.Index(fields=["module", "order"]),
        ]

    def __str__(self):
        return f"{self.module.name} - {self.name}"


class UIActionStep(BaseModel):
    """
    UI测试步骤 - POM架构的操作步骤层
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

    test_case = models.ForeignKey(
        UITestCase,
        on_delete=models.CASCADE,
        related_name="action_steps",
        verbose_name="所属测试用例"
    )
    sequence = models.IntegerField(
        verbose_name="执行顺序"
    )
    action_type = models.CharField(
        max_length=32,
        choices=ACTION_TYPE_CHOICES,
        verbose_name="操作类型"
    )
    element = models.ForeignKey(
        UIPageElement,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="action_steps",
        verbose_name="关联元素"
    )
    test_data = models.TextField(
        blank=True,
        default="",
        verbose_name="测试数据"
    )
    description = models.TextField(
        blank=True,
        default="",
        verbose_name="步骤描述"
    )

    class Meta:
        db_table = "ui_action_step"
        ordering = ["sequence"]
        verbose_name = "UI操作步骤"
        verbose_name_plural = "UI操作步骤"
        indexes = [
            models.Index(fields=["test_case", "sequence"]),
        ]

    def __str__(self):
        return f"{self.test_case.name} - Step {self.sequence}"
