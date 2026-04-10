from rest_framework import serializers
from rest_framework.exceptions import ValidationError


class BaseModelSerializers(serializers.ModelSerializer):
    """
    全局基础序列化器
    """

    def is_valid(self, *, raise_exception=False):
        """
        重写方法,拦截并格式化错误信息
        """
        # 1.先执行DRF原本的校验逻辑
        valid = super().is_valid(raise_exception=False)

        # 2.如果校验失败
        if not valid:
            # 提取友好的错误提示
            error_msg = self._get_first_error_message(self.errors)

            # 如果需求抛出异常,抛一个自定义结构的返回
            if raise_exception:
                raise ValidationError(
                    detail={"msg": error_msg, "code": 400, "data": None}
                )

            return valid

    def _get_first_error_message(self, errors):
        """
        递归解析DRF的errors字典,提取第一条最直接的报错文字
        """
        if not self.instance:
            for field, error_list in errors.items():
                field_name = field
                if hasattr(self.Meta.model, field):
                    model_field = self.Meta.model._meta.get_field(field)
                    if hasattr(model_field, "verbose_name"):
                        field_name = model_field.verbose_name

                if isinstance(error_list, list) and len(error_list) > 0:
                    return f"{field_name}: {error_list[0]}"
                elif isinstance(error_list, dict):
                    return self._get_first_error_message(error_list)

        return "参数校验失败"
