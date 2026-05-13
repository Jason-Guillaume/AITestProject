# AITestProduct/urls.py (项目根目录下的主路由)
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from assistant.analysis_lab_views import AnalysisLabReportDetailsAPIView
from common import health as common_health

urlpatterns = [
    path("health/", common_health.health_check),
    path("readiness/", common_health.readiness_check),
    path("admin/", admin.site.urls),
    # 按照模块分发到各个子应用的 urls.py 中
    path("api/sys/", include("user.sys_urls")),
    path("api/change-requests/", include("user.approval_urls")),
    path("api/user/", include("user.urls")),
    path("api/project/", include("project.urls")),
    path("api/testcase/", include("testcase.urls")),
    path("api/environments/", include("testcase.environment_urls")),
    path("api/execution/", include("execution.urls")),
    path("api/perf/", include("execution.perf_urls")),
    path("api/defect/", include("defect.urls")),
    path("api/assistant/", include("assistant.urls")),
    path("api/ai/", include("assistant.ai_urls")),
    path(
        "api/reports/<int:pk>/details/",
        AnalysisLabReportDetailsAPIView.as_view(),
        name="analysis-lab-report-details",
    ),
    path("api/server-logs/", include("server_logs.urls")),
]

# 开发环境静态提供：用于显示上传到 MEDIA_ROOT 的图片
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
