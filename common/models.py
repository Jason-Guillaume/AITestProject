from django.db import models

from django.conf import settings

# Create your models here.


class BaseModel(models.Model):
    """
    基础模型类,所有业务模型都继承此类
    用于统一公共字段
    """

    # 【创建人字段】
    # 外键关联到系统用户表 (通过 settings.AUTH_USER_MODEL 动态获取，而不是硬编码 User 模型)
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,  # 当关联用户被删除时,这里面的字段会被设置为null
        null=True,  # 允许数据库中该字段为空
        blank=True,  # 允许在django表单验证时为空
        # %(class)s 是一个魔法变量，在子类继承时会被替换为子类的类名（小写）。
        related_name="%(class)s_created",
        verbose_name="创建人",
    )
    updater = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="%(class)s_updated",
        verbose_name="更新人",
    )
    create_time = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    update_time = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    is_deleted = models.BooleanField(default=False, verbose_name="是否已删除")

    class Meta:
        abstract = True  # 标记为抽象类,django不会在数据库中为他单独建表
