import base64
import secrets
import string
import uuid
import re

from rest_framework.authtoken.models import Token
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from django.core.cache import cache
from common.views import *
from common.models import AuditEvent
from user.models import *
from user.serialize import *
from user.serialize import UserRegisterSerializer
from user.serialize import (
    UserProfileSerializer,
    UserSensitiveChangeRequestCreateSerializer,
    UserChangeRequestListSerializer,
    UserChangeRequestDecisionSerializer,
    SystemMessageSerializer,
)
from django.contrib.auth.models import Group
from rest_framework.pagination import PageNumberPagination
from rest_framework import viewsets

from user.permissions import IsSystemAdmin, IsApprovalAdmin
from user.models import UserChangeRequest, SystemMessage
from user.change_request_actions import approve_change_request, reject_change_request

# Create your views here.


class UserViewSet(BaseModelViewSet):
    queryset = User.objects.filter(is_deleted=False)
    serializer_class = UserSerializer

    def get_permissions(self):
        if self.action in ["create", "destroy"]:
            return [IsSystemAdmin()]
        return super().get_permissions()

    def get_queryset(self):
        qs = super().get_queryset()
        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated:
            return qs.none()
        if bool(getattr(user, "is_system_admin", False)):
            return qs.order_by("-id")
        # 普通用户：仅可见同项目成员 + 自己（用于成员选择）
        try:
            my_projects = user.projects.all()
            qs = qs.filter(Q(projects__in=my_projects) | Q(pk=user.pk)).distinct()
        except Exception:
            qs = qs.filter(pk=user.pk)
        return qs.order_by("id")


class SystemPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = "page_size"
    max_page_size = 100


class OrganizationViewSet(BaseModelViewSet):
    queryset = Organization.objects.all()
    serializer_class = OrganizationSerializer
    pagination_class = SystemPagination

    def get_permissions(self):
        perms = super().get_permissions()
        return [*perms, IsSystemAdmin()]

    def get_queryset(self):
        qs = super().get_queryset()
        name = self.request.query_params.get("name")
        if name:
            qs = qs.filter(org_name__icontains=name)
        return qs.prefetch_related("members").order_by("-create_time")


class SystemMessageSettingViewSet(BaseModelViewSet):
    queryset = SystemMessageSetting.objects.all()
    serializer_class = SystemMessageSettingSerializer
    pagination_class = SystemPagination

    def get_queryset(self):
        qs = super().get_queryset()
        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated:
            return qs.none()
        qs = qs.filter(recipient=user)
        # 允许只取最近一条设置（用于前端编辑）
        latest = self.request.query_params.get("latest")
        if latest == "1":
            return qs.order_by("-create_time")[:1]
        return qs.order_by("-create_time")

    def perform_create(self, serializer):
        user = getattr(self.request, "user", None)
        if not user or not user.is_authenticated:
            raise ValidationError({"detail": "未登录"})
        instance, _ = SystemMessageSetting.objects.update_or_create(
            recipient=user,
            defaults=serializer.validated_data,
        )
        serializer.instance = instance


class RoleViewSet(viewsets.ModelViewSet):
    """
    角色管理：使用 Django auth 的 Group
    """

    queryset = Group.objects.all()
    serializer_class = RoleSerializer

    def get_permissions(self):
        perms = super().get_permissions()
        return [*perms, IsSystemAdmin()]


class CaptchaAPIView(APIView):
    """
    获取图片验证码接口
    """

    authentication_classes = []
    permission_classes = []

    def get_client_ip(self, request):
        xff = request.META.get("HTTP_X_FORWARDED_FOR")
        if xff:
            return xff.split(",")[0].strip()
        return (request.META.get("REMOTE_ADDR") or "").strip() or "unknown"

    def get(self, request, *args, **kwargs):
        try:
            from captcha.image import ImageCaptcha
        except ImportError:
            return Response(
                {
                    "code": 500,
                    "msg": "服务端未安装验证码依赖，请执行: pip install captcha",
                    "data": None,
                },
                status=500,
            )

        # IP 频率限制（每分钟最多 10 次）
        ip = self.get_client_ip(request)
        limit_key = f"captcha_limit_{ip}"
        cur = cache.get(limit_key, 0)
        try:
            cur = int(cur)
        except (TypeError, ValueError):
            cur = 0
        if cur >= 10:
            return Response(
                {"code": 429, "msg": "请求过于频繁", "data": None}, status=429
            )
        cache.set(limit_key, cur + 1, timeout=60)

        # 1.生产四位随机字符（使用 secrets）
        chars = string.ascii_uppercase + string.digits
        code = "".join(secrets.choice(chars) for _ in range(4))

        # 2.生成唯一标识
        captcha_uuid = str(uuid.uuid4())

        # 3.将验证码存放django缓存
        try:
            cache.set(f"captcha_{captcha_uuid}", code, timeout=300)
        except Exception:
            return Response(
                {
                    "code": 500,
                    "msg": "缓存服务不可用（可能未启动 Redis），请稍后重试或检查配置",
                    "data": None,
                },
                status=500,
            )

        # 4. 清爽科技风验证码（白底、科技蓝字、弱噪声）
        try:
            from user.captcha_image import CleanTechCaptcha
        except ImportError:
            CleanTechCaptcha = None
        CaptchaCls = CleanTechCaptcha if CleanTechCaptcha else ImageCaptcha
        image = CaptchaCls(width=120, height=40, font_sizes=(30, 34, 38))
        image_data = image.generate(
            code,
            bg_color=(255, 255, 255),
            fg_color=(37, 99, 235),
        )

        # 5.将图片二进制数据转换为Base64编码,方面前端直接展示
        base64_str = base64.b64encode(image_data.getvalue()).decode("utf-8")
        base64_image = f"data:image/png;base64,{base64_str}"

        # 6.返回给前端
        return Response(
            {
                "code": 200,
                "msg": "获取验证码成功",
                "data": {"uuid": captcha_uuid, "image": base64_image},
            }
        )


class UserRegisterAPIView(APIView):
    """
    用户注册接口
    """

    # 注册接口必须对外开放,取消认证和权限校验
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        # 1.实例化序列化器
        serializer = UserRegisterSerializer(data=request.data)

        # 2.触发校验,失败自动抛出异常
        serializer.is_valid(raise_exception=True)

        # 3.校验通过,保存数据,触发序列化器的拦截加密
        serializer.save()

        return Response({"code": 200, "msg": "注册成功", "data": None})


class UserLoginAPIView(APIView):
    """
    用户登录接口
    """

    # 登录接口必须对外开放，取消认证和权限校验
    authentication_classes = []
    permission_classes = []

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 从刚才序列化器 validate 方法里拿到真正的用户对象
        user = serializer.validated_data["user"]
        try:
            user.refresh_from_db()
        except Exception:
            pass

        # 核心：获取或创建该用户的 Token
        # 如果该用户之前登录过，就会取出旧Token；如果是首次登录，会生成新Token
        token, created = Token.objects.get_or_create(user=user)

        return Response(
            {
                "code": 200,
                "msg": "登录成功",
                "data": {
                    "token": token.key,  # 前端需要的凭证
                    "username": user.username,
                    "real_name": user.real_name,
                    "user_id": user.id,
                    "is_system_admin": bool(getattr(user, "is_system_admin", False)),
                },
            }
        )


class CurrentUserAPIView(APIView):
    """
    当前登录用户信息（用于同步前端 is_system_admin 与展示名）
    """

    def get(self, request):
        user = request.user
        if not user.is_authenticated:
            return Response(
                {"code": 401, "msg": "未登录", "data": None},
                status=401,
            )
        return Response(
            {
                "code": 200,
                "msg": "ok",
                "data": {
                    "user_id": user.id,
                    "username": user.username,
                    "real_name": getattr(user, "real_name", None) or "",
                    "is_system_admin": bool(getattr(user, "is_system_admin", False)),
                },
            }
        )


class ChangePasswordAPIView(APIView):
    """
    修改密码（需要登录）
    """

    def post(self, request):
        # TokenAuthentication + IsAuthenticated 会由全局 REST_FRAMEWORK 默认提供
        user = request.user

        old_password = request.data.get("old_password") or ""
        new_password = request.data.get("new_password") or ""
        confirm_password = request.data.get("confirm_password") or ""
        if len(new_password) < 8:
            return Response(
                {"code": 400, "msg": "密码长度至少 8 位", "data": None}, status=400
            )
        if not re.search(r"[A-Z]", new_password):
            return Response(
                {"code": 400, "msg": "密码需包含大写字母", "data": None}, status=400
            )
        if not re.search(r"[a-z]", new_password):
            return Response(
                {"code": 400, "msg": "密码需包含小写字母", "data": None}, status=400
            )
        if not re.search(r"\d", new_password):
            return Response(
                {"code": 400, "msg": "密码需包含数字", "data": None}, status=400
            )

        if not old_password:
            return Response(
                {"code": 400, "msg": "请输入旧密码", "data": None},
                status=400,
            )
        if not new_password:
            return Response(
                {"code": 400, "msg": "请输入新密码", "data": None},
                status=400,
            )
        if new_password != confirm_password:
            return Response(
                {"code": 400, "msg": "两次输入的新密码不一致", "data": None},
                status=400,
            )

        if not user or not user.is_authenticated:
            return Response(
                {"code": 401, "msg": "未登录", "data": None},
                status=401,
            )

        if not user.check_password(old_password):
            return Response(
                {"code": 400, "msg": "旧密码不正确", "data": None},
                status=400,
            )

        user.set_password(new_password)
        user.save(update_fields=["password"])

        return Response({"code": 200, "msg": "密码修改成功", "data": None})


class UserProfileAPIView(APIView):
    """
    用户中心：直接更新头像、真实姓名、手机号、邮箱（不涉及用户名/登录密码审批）。
    GET / PATCH 均支持；PATCH 可使用 multipart 上传 avatar。
    """

    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def get(self, request):
        serializer = UserProfileSerializer(request.user, context={"request": request})
        return Response({"code": 200, "msg": "ok", "data": serializer.data})

    def patch(self, request):
        serializer = UserProfileSerializer(
            request.user,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"code": 200, "msg": "资料已更新", "data": serializer.data})


class UserMyPendingSensitiveStatusAPIView(APIView):
    """
    当前用户待审批的敏感变更（用户名 / 密码各最多一条 pending）。
    """

    def get(self, request):
        pending_types = UserChangeRequest.objects.filter(
            user=request.user,
            status=UserChangeRequest.Status.PENDING,
        ).values_list("request_type", flat=True)
        pending_set = set(pending_types)
        return Response(
            {
                "code": 200,
                "msg": "ok",
                "data": {
                    "pending_username": UserChangeRequest.RequestType.USERNAME
                    in pending_set,
                    "pending_password": UserChangeRequest.RequestType.PASSWORD
                    in pending_set,
                },
            }
        )


class UserSensitiveChangeRequestAPIView(APIView):
    """
    提交敏感信息变更：username 或 password，生成 UserChangeRequest(pending)。
    由信号在事务提交后为管理员批量创建 SystemMessage（站内信），不发送邮件。
    """

    def post(self, request):
        serializer = UserSensitiveChangeRequestCreateSerializer(
            data=request.data, context={"request": request}
        )
        serializer.is_valid(raise_exception=True)
        obj = serializer.save()
        return Response(
            {
                "code": 200,
                "msg": "已提交申请，请等待管理员在站内消息中审批",
                "data": {"id": obj.id, "status": obj.status},
            }
        )


class SystemMessageListAPIView(APIView):
    """
    当前登录用户收件箱：默认仅返回发给自己的 SystemMessage（管理员各自待办）。
    查询参数：is_read=0|1|true|false
    """

    def get(self, request):
        try:
            qs = SystemMessage.objects.filter(recipient=request.user).order_by(
                "-created_at"
            )
            raw = (request.query_params.get("is_read") or "").lower()
            if raw in ("0", "false"):
                qs = qs.filter(is_read=False)
            elif raw in ("1", "true"):
                qs = qs.filter(is_read=True)
            serializer = SystemMessageSerializer(qs, many=True)
            return Response({"code": 200, "msg": "ok", "data": serializer.data})
        except RuntimeError as exc:
            # 开发环境重启/解释器关闭瞬间可能出现：
            # RuntimeError: cannot schedule new futures after interpreter shutdown
            if "cannot schedule new futures after interpreter shutdown" in str(exc):
                return Response(
                    {
                        "code": 503,
                        "msg": "服务正在重启，请稍后重试",
                        "data": [],
                    },
                    status=503,
                )
            raise


class SystemMessageMarkReadAPIView(APIView):
    """将一条站内信标记为已读（仅能操作自己的）。"""

    def patch(self, request, pk):
        try:
            n = SystemMessage.objects.filter(pk=pk, recipient=request.user).update(
                is_read=True
            )
            if not n:
                return Response(
                    {"code": 404, "msg": "消息不存在", "data": None},
                    status=404,
                )
            return Response({"code": 200, "msg": "ok", "data": {"id": pk}})
        except RuntimeError as exc:
            if "cannot schedule new futures after interpreter shutdown" in str(exc):
                return Response(
                    {
                        "code": 503,
                        "msg": "服务正在重启，请稍后重试",
                        "data": None,
                    },
                    status=503,
                )
            raise


class UserAuditEventListAPIView(APIView):
    """
    当前用户审计事件查询（只读）：
    GET /api/user/me/audit/events/?page=1&page_size=50
    - 普通用户：仅返回自己产生的审计事件（creator=self）
    - 系统管理员全量审计请使用：GET /api/sys/audit/events/
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            page = int(request.query_params.get("page", "1"))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(request.query_params.get("page_size", "50"))
        except (TypeError, ValueError):
            page_size = 50
        page = max(1, page)
        page_size = max(1, min(page_size, 200))
        offset = (page - 1) * page_size

        action = (request.query_params.get("action") or "").strip()
        object_app = (request.query_params.get("object_app") or "").strip()
        object_model = (request.query_params.get("object_model") or "").strip()
        object_id = (request.query_params.get("object_id") or "").strip()

        qs = AuditEvent.objects.filter(is_deleted=False, creator=request.user)
        if action:
            qs = qs.filter(action=action)
        if object_app:
            qs = qs.filter(object_app=object_app)
        if object_model:
            qs = qs.filter(object_model=object_model)
        if object_id:
            qs = qs.filter(object_id=object_id)

        total = qs.count()
        qs = qs.order_by("-create_time")[offset : offset + page_size]
        rows = list(
            qs.values(
                "id",
                "action",
                "object_app",
                "object_model",
                "object_id",
                "object_repr",
                "request_path",
                "ip",
                "extra",
                "create_time",
            )
        )
        return Response(
            {
                "code": 200,
                "msg": "ok",
                "data": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "items": rows,
                },
            }
        )


class AdminUserChangeRequestListAPIView(APIView):
    """管理员：查看敏感变更申请列表。"""

    def get_permissions(self):
        return [*super().get_permissions(), IsApprovalAdmin()]

    def get(self, request):
        status = request.query_params.get("status")
        qs = UserChangeRequest.objects.select_related("user").order_by("-created_at")
        if status:
            qs = qs.filter(status=status)
        serializer = UserChangeRequestListSerializer(qs, many=True)
        return Response({"code": 200, "msg": "ok", "data": serializer.data})


class AdminChangeRequestApproveAPIView(APIView):
    """POST /api/change-requests/<id>/approve/ — 通过申请并标记关联站内信已读。"""

    permission_classes = [IsApprovalAdmin]

    def post(self, request, pk):
        try:
            cr = UserChangeRequest.objects.select_related("user").get(pk=pk)
        except UserChangeRequest.DoesNotExist:
            return Response(
                {"code": 404, "msg": "记录不存在", "data": None},
                status=404,
            )
        try:
            approve_change_request(
                cr, approver=request.user if request.user.is_authenticated else None
            )
        except ValueError as e:
            return Response(
                {"code": 400, "msg": str(e), "data": None},
                status=400,
            )
        return Response(
            {
                "code": 200,
                "msg": "已通过并已生效",
                "data": {"id": cr.id},
            }
        )


class AdminChangeRequestRejectAPIView(APIView):
    """POST /api/change-requests/<id>/reject/ — 拒绝并标记关联站内信已读。"""

    permission_classes = [IsApprovalAdmin]

    def post(self, request, pk):
        try:
            cr = UserChangeRequest.objects.select_related("user").get(pk=pk)
        except UserChangeRequest.DoesNotExist:
            return Response(
                {"code": 404, "msg": "记录不存在", "data": None},
                status=404,
            )
        try:
            reject_change_request(
                cr, approver=request.user if request.user.is_authenticated else None
            )
        except ValueError as e:
            return Response(
                {"code": 400, "msg": str(e), "data": None},
                status=400,
            )
        return Response({"code": 200, "msg": "已拒绝", "data": {"id": cr.id}})


class AdminUserChangeRequestDecisionAPIView(APIView):
    """兼容旧版：POST body `{ \"decision\": \"approve\"|\"reject\" }`。"""

    def get_permissions(self):
        return [*super().get_permissions(), IsApprovalAdmin()]

    def post(self, request, pk):
        try:
            cr = UserChangeRequest.objects.select_related("user").get(pk=pk)
        except UserChangeRequest.DoesNotExist:
            return Response(
                {"code": 404, "msg": "记录不存在", "data": None},
                status=404,
            )

        dec = UserChangeRequestDecisionSerializer(data=request.data)
        dec.is_valid(raise_exception=True)
        decision = dec.validated_data["decision"]

        try:
            if decision == "reject":
                reject_change_request(
                    cr, approver=request.user if request.user.is_authenticated else None
                )
            else:
                approve_change_request(
                    cr, approver=request.user if request.user.is_authenticated else None
                )
        except ValueError as e:
            return Response(
                {"code": 400, "msg": str(e), "data": None},
                status=400,
            )

        msg = "已拒绝" if decision == "reject" else "已通过并已生效"
        return Response({"code": 200, "msg": msg, "data": {"id": cr.id}})
