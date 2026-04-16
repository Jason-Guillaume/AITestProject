from django.urls import path

from user.sys_views import (
    AIModelConfigAPIView,
    AIModelConfigDisconnectAPIView,
    AIModelConfigReconnectAPIView,
  AiQuotaPolicyDetailAPIView,
  AiQuotaPolicyListCreateAPIView,
    AiUsageEventListAPIView,
    AiUsageMetricsAPIView,
    AiUsageSummaryAPIView,
    AiUsageLatencyTrendAPIView,
    AiUsageTopErrorsAPIView,
    AiUsageExportCsvAPIView,
    AuditEventListAPIView,
    AuditEventExportCsvAPIView,
)

urlpatterns = [
    path("ai-config/", AIModelConfigAPIView.as_view()),
    path("ai-config/disconnect/", AIModelConfigDisconnectAPIView.as_view()),
    path("ai-config/reconnect/", AIModelConfigReconnectAPIView.as_view()),
  path("ai-quota/policies/", AiQuotaPolicyListCreateAPIView.as_view()),
  path("ai-quota/policies/<int:policy_id>/", AiQuotaPolicyDetailAPIView.as_view()),
    path("ai-usage/events/", AiUsageEventListAPIView.as_view()),
    path("ai-usage/summary/", AiUsageSummaryAPIView.as_view()),
    path("ai-usage/metrics/", AiUsageMetricsAPIView.as_view()),
    path("ai-usage/top-errors/", AiUsageTopErrorsAPIView.as_view()),
    path("ai-usage/latency-trend/", AiUsageLatencyTrendAPIView.as_view()),
    path("ai-usage/export.csv", AiUsageExportCsvAPIView.as_view()),
    path("audit/events/", AuditEventListAPIView.as_view()),
    path("audit/export.csv", AuditEventExportCsvAPIView.as_view()),
]
