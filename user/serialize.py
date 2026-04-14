from django.conf import settings
from django.contrib.auth import authenticate
from django.core.cache import cache

from common.serialize import *
from django.contrib.auth.hashers import make_password

from user.models import User
from user.models import (
    AIModelConfig,
    Organization,
    SystemMessage,
    SystemMessageSetting,
    UserChangeRequest,
)
from django.contrib.auth.models import Group


class UserSerializer(BaseModelSerializers):
    creator_name = serializers.CharField(source="creator.real_name", read_only=True)

    class Meta:
        model = User
        fields = "__all__"
        read_only_fields = ("creator", "updater", "create_time", "update_time")

    def create(self, validated_data):
        """
        重写创建逻辑，确保密码加密且其它字段能正确落库。
        """
        groups = validated_data.pop("groups", [])
        user_permissions = validated_data.pop("user_permissions", [])
        password = validated_data.pop("password")
        user = User.objects.create_user(
            password=password,
            **validated_data,
        )
        if groups:
            user.groups.set(groups)
        if user_permissions:
            user.user_permissions.set(user_permissions)
        return user

class UserRegisterSerializer(serializers.Serializer):
    """
    用户注册使用的序列化器
    """
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128)
    email = serializers.EmailField(required=False, allow_blank=True)
    phone_number = serializers.CharField(max_length=32, required=False, allow_blank=True)
    captcha_code = serializers.CharField(max_length=4, write_only=True, help_text="用户输入的验证码")
    captcha_uuid = serializers.CharField(write_only=True, help_text="获取验证码时返回的UUID")

    def validate(self, attrs):
        #1.取出前端传来的验证码和UUID
        user_code = attrs.get('captcha_code')
        uuid = attrs.get('captcha_uuid')

        #2,从缓存中获取真实的验证码
        cache_key = f"captcha_{uuid}"
        real_code = cache.get(cache_key)

        #3.检验逻辑
        if not real_code:
            raise serializers.ValidationError({"captcha_code": "验证码已过期或无效，请重新获取"})

        #忽略大小写进行比对
        if real_code.lower() != user_code.lower():
            raise serializers.ValidationError({"captcha_code": "验证码错误"})

        #验证通过后,将缓存中的验证码删掉
        cache.delete(cache_key)

        #清理不需要存入数据库的字段
        attrs.pop('captcha_code')
        attrs.pop('captcha_uuid')

        email = (attrs.get("email") or "").strip()
        phone = (attrs.get("phone_number") or "").strip()
        if email:
            if User.objects.filter(email=email).exists():
                raise serializers.ValidationError({"email": "邮箱已被注册"})
            attrs["email"] = email
        if phone:
            if User.objects.filter(phone_number=phone).exists():
                raise serializers.ValidationError({"phone_number": "手机号已被注册"})
            attrs["phone_number"] = phone
        return attrs

    def create(self, validated_data):
        """
        必须实现 create 方法来接管 serializer.save() 的逻辑
        """
        # 注意：这里必须使用 User.objects.create_user，它会自动将 password 字段进行 Hash 加密
        # 如果使用 User.objects.create()，密码将是明文，导致后续无法登录
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password'],
            real_name=validated_data.get('real_name', ''),
            email=validated_data.get("email", "") or "",
            phone_number=validated_data.get("phone_number", "") or "",
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    用户登录使用的序列化器
    """
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128)

    def validate(self, attrs):
        username = (attrs.get("username") or "").strip()
        password = attrs.get("password") or ""
        attrs["username"] = username

        if not username:
            raise serializers.ValidationError({"detail": "请输入用户名"})

        user = authenticate(username=username, password=password)
        if user:
            if getattr(user, "is_deleted", False):
                raise serializers.ValidationError({"detail": "账号不可用"})
            if not user.is_active:
                raise serializers.ValidationError({"detail": "该账号已被禁用"})
            attrs["user"] = user
            return attrs
        raise serializers.ValidationError({"detail": "账号或密码错误，请重试"})


class OrganizationSerializer(BaseModelSerializers):
    creator_name = serializers.CharField(source="creator.real_name", read_only=True)

    class Meta:
        model = Organization
        fields = "__all__"
        read_only_fields = ("creator", "updater", "create_time", "update_time")


class SystemMessageSettingSerializer(BaseModelSerializers):
    creator_name = serializers.CharField(source="creator.real_name", read_only=True)

    class Meta:
        model = SystemMessageSetting
        fields = "__all__"
        read_only_fields = ("creator", "updater", "create_time", "update_time")


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ["id", "name"]


# ---------------------------------------------------------------------------
# 用户中心：资料直接更新 / 敏感信息审批流
# ---------------------------------------------------------------------------


class UserProfileSerializer(BaseModelSerializers):
    """
    个人中心：可直接修改展示名、手机、邮箱、头像（ImageField 上传）。
    username / id 只读；敏感项走 UserChangeRequest。
    """

    avatar_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "real_name",
            "phone_number",
            "email",
            "avatar",
            "avatar_url",
        ]
        read_only_fields = ["id", "username", "avatar_url"]

    def get_avatar_url(self, obj):
        if not obj.avatar:
            return None
        try:
            url = obj.avatar.url
        except ValueError:
            return None
        request = self.context.get("request")
        if request:
            return request.build_absolute_uri(url)
        return url

    def validate_avatar(self, value):
        if value is None:
            return value
        max_size = 2 * 1024 * 1024
        if int(getattr(value, "size", 0) or 0) > max_size:
            raise serializers.ValidationError("头像大小不能超过 2MB")
        ext = (str(getattr(value, "name", "")).rsplit(".", 1)[-1] or "").lower()
        if ext not in {"jpg", "jpeg", "png", "webp", "gif"}:
            raise serializers.ValidationError("头像仅支持 jpg/jpeg/png/webp/gif")
        return value


class UserSensitiveChangeRequestCreateSerializer(serializers.Serializer):
    """提交用户名或密码变更申请（密码仅接收明文，入库为 Django 哈希）。"""

    request_type = serializers.ChoiceField(choices=UserChangeRequest.RequestType.choices)
    new_username = serializers.CharField(
        max_length=150, required=False, allow_blank=True
    )
    new_password = serializers.CharField(
        max_length=128, write_only=True, required=False, allow_blank=True
    )

    def validate(self, attrs):
        user = self.context["request"].user
        rt = attrs["request_type"]
        if rt == UserChangeRequest.RequestType.USERNAME:
            nu = (attrs.get("new_username") or "").strip()
            if not nu:
                raise serializers.ValidationError(
                    {"new_username": "请填写新用户名"}
                )
            if nu == user.username:
                raise serializers.ValidationError(
                    {"new_username": "与当前用户名相同"}
                )
            if User.objects.filter(username=nu).exclude(pk=user.pk).exists():
                raise serializers.ValidationError(
                    {"new_username": "该用户名已被占用"}
                )
            attrs["new_username"] = nu
        elif rt == UserChangeRequest.RequestType.PASSWORD:
            pw = attrs.get("new_password") or ""
            if not pw:
                raise serializers.ValidationError(
                    {"new_password": "请填写新密码"}
                )
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        rt = validated_data["request_type"]
        if UserChangeRequest.objects.filter(
            user=user,
            request_type=rt,
            status=UserChangeRequest.Status.PENDING,
        ).exists():
            raise serializers.ValidationError(
                {"detail": "您已有待审批的同类申请，请等待管理员处理"}
            )

        if rt == UserChangeRequest.RequestType.USERNAME:
            new_value = validated_data["new_username"]
        else:
            new_value = make_password(validated_data["new_password"])

        return UserChangeRequest.objects.create(
            user=user,
            request_type=rt,
            new_value=new_value,
            status=UserChangeRequest.Status.PENDING,
        )


class UserChangeRequestListSerializer(serializers.ModelSerializer):
    """管理员列表：密码类不返回具体哈希。"""

    applicant_username = serializers.CharField(
        source="user.username", read_only=True
    )
    safe_new_value = serializers.SerializerMethodField()

    class Meta:
        model = UserChangeRequest
        fields = [
            "id",
            "user",
            "applicant_username",
            "request_type",
            "safe_new_value",
            "status",
            "created_at",
            "updated_at",
        ]

    def get_safe_new_value(self, obj):
        if obj.request_type == UserChangeRequest.RequestType.PASSWORD:
            return "********"
        return obj.new_value


class UserChangeRequestDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("approve", "reject"))


class SystemMessageSerializer(serializers.ModelSerializer):
    """当前用户收件箱（列表 / 详情）。"""

    related_request = serializers.PrimaryKeyRelatedField(
        read_only=True, allow_null=True
    )

    class Meta:
        model = SystemMessage
        fields = [
            "id",
            "title",
            "content",
            "is_read",
            "related_request",
            "created_at",
        ]
        read_only_fields = fields


# ---- 全局 AI 模型配置 ----

AI_MODEL_DISPLAY_NAMES = {
    "glm-4.7-flash": "GLM-4.7-Flash",
    "glm-4": "GLM-4",
    "glm-4-flash": "GLM-4-Flash",
    "glm-4-plus": "GLM-4-Plus",
    "iflytek-spark-maas-coding": "iFLYTEK Spark MaaS Coding",
    "astron-code-latest": "Astron Coding",
    "wenxin": "文心大模型 5.0",
    "gpt-4o": "GPT-4o",
    "claude-3-5-sonnet": "Claude 3.5",
    "qwen-turbo": "通义千问",
}

IFLYTEK_MAAS_MODEL_TYPE = "iflytek-spark-maas-coding"
IFLYTEK_MAAS_OPENAI_BASE = "https://maas-coding-api.cn-huabei-1.xf-yun.com/v2"


def ai_model_display_name(model_type: str) -> str:
    t = (model_type or "").strip()
    if not t:
        return "未知模型"
    return AI_MODEL_DISPLAY_NAMES.get(t.lower(), t)


class AIModelConfigReadSerializer(serializers.ModelSerializer):
    model_display_name = serializers.SerializerMethodField()

    class Meta:
        model = AIModelConfig
        fields = (
            "id",
            "model_type",
            "model_display_name",
            "base_url",
            "is_connected",
            "updated_at",
        )

    def get_model_display_name(self, obj):
        return ai_model_display_name(obj.model_type)


class AIModelConfigWriteSerializer(serializers.Serializer):
    model_type = serializers.CharField(max_length=64)
    api_key = serializers.CharField(required=False, allow_blank=True, write_only=True)
    base_url = serializers.CharField(
        required=False, allow_blank=True, default=""
    )

    def validate_model_type(self, value):
        v = (value or "").strip()
        if not v:
            raise serializers.ValidationError("请选择或填写模型类型")
        return v

    def validate(self, attrs):
        mt = (attrs.get("model_type") or "").strip().lower()
        attrs["model_type"] = mt
        key = (attrs.get("api_key") or "").strip()
        if not key and self.instance is None:
            raise serializers.ValidationError({"api_key": "请填写 API Key"})
        if key:
            attrs["api_key"] = key
        else:
            attrs.pop("api_key", None)
        base = (attrs.get("base_url") or "").strip()
        if mt == IFLYTEK_MAAS_MODEL_TYPE:
            # 支持编辑；若未填写则默认 v1 根路径（由后端统一拼接 /chat/completions）。
            base = base or IFLYTEK_MAAS_OPENAI_BASE
        attrs["base_url"] = base
        return attrs

    def create(self, validated_data):
        AIModelConfig.objects.all().delete()
        return AIModelConfig.objects.create(
            model_type=validated_data["model_type"],
            api_key=validated_data["api_key"],
            base_url=validated_data.get("base_url", ""),
            is_connected=True,
        )

    def update(self, instance, validated_data):
        instance.model_type = validated_data["model_type"]
        if "api_key" in validated_data:
            instance.api_key = validated_data["api_key"]
        if "base_url" in validated_data:
            instance.base_url = validated_data["base_url"]
        instance.is_connected = True
        instance.save()
        return instance

    def save(self, **kwargs):
        validated_data = {**self.validated_data, **kwargs}
        if self.instance is None:
            self.instance = self.create(validated_data)
        else:
            self.instance = self.update(self.instance, validated_data)
        return self.instance