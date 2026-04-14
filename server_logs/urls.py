from django.urls import path
from rest_framework.routers import DefaultRouter

from server_logs.views import (
    AnalyzeLogAPIView,
    AnalyzeLogWithContextAPIView,
    LogAutoTicketCreateDefectAPIView,
    LogAutoTicketEnqueueAPIView,
    LogAutoTicketJobDetailAPIView,
    LogErrorTrendAPIView,
    LogHistorySearchAPIView,
    LogServerOrganizationChoicesAPIView,
    RemoteLogServerViewSet,
    ServerLogAuditViewSet,
)

router = DefaultRouter()
router.register("hosts", RemoteLogServerViewSet, basename="remote-log-server")
router.register("audit-events", ServerLogAuditViewSet, basename="server-log-audit")

urlpatterns = router.urls + [
    path("analyze/", AnalyzeLogAPIView.as_view(), name="server-logs-analyze"),
    path(
        "analyze-with-context/",
        AnalyzeLogWithContextAPIView.as_view(),
        name="server-logs-analyze-with-context",
    ),
    path("search/", LogHistorySearchAPIView.as_view(), name="server-logs-search"),
    path("agg/error-trend/", LogErrorTrendAPIView.as_view(), name="server-logs-error-trend"),
    path(
        "organization-choices/",
        LogServerOrganizationChoicesAPIView.as_view(),
        name="server-logs-org-choices",
    ),
    path(
        "auto-tickets/enqueue/",
        LogAutoTicketEnqueueAPIView.as_view(),
        name="server-logs-auto-ticket-enqueue",
    ),
    path(
        "auto-tickets/jobs/<int:job_id>/create-defect/",
        LogAutoTicketCreateDefectAPIView.as_view(),
        name="server-logs-auto-ticket-create-defect",
    ),
    path(
        "auto-tickets/jobs/<int:job_id>/",
        LogAutoTicketJobDetailAPIView.as_view(),
        name="server-logs-auto-ticket-job",
    ),
]
