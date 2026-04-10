"""系统级接口：全局 AI 模型配置（/api/sys/）"""

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from user.models import AIModelConfig
from user.permissions import IsSystemAdmin
from user.serialize import AIModelConfigReadSerializer, AIModelConfigWriteSerializer


class AIModelConfigAPIView(APIView):
    """
    GET /api/sys/ai-config/ — 任意登录用户可查看当前配置状态（不含明文 Key）
    PUT /api/sys/ai-config/ — 系统管理员保存/更新配置；保存后 is_connected=True
    DELETE /api/sys/ai-config/ — 系统管理员删除配置记录
    """

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsSystemAdmin()]

    def get(self, request):
        row = AIModelConfig.objects.order_by("id").first()
        if not row:
            return Response({"code": 200, "msg": "ok", "data": None})
        return Response(
            {
                "code": 200,
                "msg": "ok",
                "data": AIModelConfigReadSerializer(row).data,
            }
        )

    def put(self, request):
        row = AIModelConfig.objects.order_by("id").first()
        ser = AIModelConfigWriteSerializer(instance=row, data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save()
        row = AIModelConfig.objects.order_by("id").first()
        return Response(
            {
                "code": 200,
                "msg": "保存成功",
                "data": AIModelConfigReadSerializer(row).data,
            }
        )

    def delete(self, request):
        deleted, _ = AIModelConfig.objects.all().delete()
        if not deleted:
            return Response(
                {"code": 400, "msg": "当前没有可删除的配置", "data": None},
                status=200,
            )
        return Response({"code": 200, "msg": "已删除", "data": None})


class AIModelConfigDisconnectAPIView(APIView):
    """POST /api/sys/ai-config/disconnect/ — 标记断开，不删除 Key"""

    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def post(self, request):
        row = AIModelConfig.objects.order_by("id").first()
        if not row:
            return Response(
                {"code": 404, "msg": "未配置 AI 模型", "data": None},
                status=200,
            )
        row.is_connected = False
        row.save(update_fields=["is_connected", "updated_at"])
        return Response(
            {
                "code": 200,
                "msg": "已断开连接",
                "data": AIModelConfigReadSerializer(row).data,
            }
        )


class AIModelConfigReconnectAPIView(APIView):
    """POST /api/sys/ai-config/reconnect/ — 在保留 Key 的前提下重新标记为已连接"""

    permission_classes = [IsAuthenticated, IsSystemAdmin]

    def post(self, request):
        row = AIModelConfig.objects.order_by("id").first()
        if not row:
            return Response(
                {"code": 404, "msg": "未配置 AI 模型", "data": None},
                status=200,
            )
        row.is_connected = True
        row.save(update_fields=["is_connected", "updated_at"])
        return Response(
            {
                "code": 200,
                "msg": "已重新连接",
                "data": AIModelConfigReadSerializer(row).data,
            }
        )
