from django.db import models
from django.db.models import UniqueConstraint
from common.models import BaseModel


class TestDefect(BaseModel):
    defect_no = models.CharField(max_length=255, verbose_name="缺陷编号")
    defect_name = models.CharField(max_length=255, verbose_name="缺陷标题")
    release_version = models.ForeignKey(
        "project.ReleasePlan",
        on_delete=models.SET_NULL,
        null=True,
        related_name="defects",
        verbose_name="关联版本",
    )
    severity = models.IntegerField(
        choices=[(1, "致命"), (2, "严重"), (3, "一般"), (4, "建议")],
        default=3,
        verbose_name="严重程度",
    )
    priority = models.IntegerField(
        choices=[(1, "高"), (2, "中"), (3, "低")], default=2, verbose_name="优先级"
    )
    status = models.IntegerField(
        choices=[(1, "新缺陷"), (2, "处理中"), (3, "已拒绝"), (4, "已关闭")],
        default=1,
        verbose_name="状态",
    )
    handler = models.ForeignKey(
        "user.User",
        on_delete=models.PROTECT,
        related_name="handled_defects",
        verbose_name="当前处理人",
    )
    module = models.ForeignKey(
        "testcase.TestModule",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="defects",
        verbose_name="所属模块",
    )
    defect_content = models.TextField(null=True, blank=True, verbose_name="缺陷内容")
    reproduction_steps = models.JSONField(
        default=list, blank=True, verbose_name="复现步骤"
    )
    attachments = models.JSONField(default=list, blank=True, verbose_name="附件列表")
    environment = models.CharField(
        max_length=255, blank=True, default="", verbose_name="发生环境"
    )

    class Meta:
        db_table = "test_defect"
        constraints = [
            UniqueConstraint(
                fields=["defect_no", "is_deleted"],
                name="uniq_test_defect_no_is_deleted",
            )
        ]
