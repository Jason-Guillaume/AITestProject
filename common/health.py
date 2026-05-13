from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache


def health_check(request):
    status = {"status": "healthy", "checks": {}}
    overall = True

    try:
        connection.ensure_connection()
        status["checks"]["database"] = "ok"
    except Exception as e:
        status["checks"]["database"] = f"error: {str(e)[:100]}"
        overall = False

    try:
        cache.set("_health_check", "1", 5)
        val = cache.get("_health_check")
        status["checks"]["cache"] = "ok" if val == "1" else "degraded"
    except Exception as e:
        status["checks"]["cache"] = f"error: {str(e)[:100]}"
        overall = False

    status["status"] = "healthy" if overall else "degraded"
    code = 200 if overall else 503
    return JsonResponse(status, status=code)


def readiness_check(request):
    try:
        connection.ensure_connection()
        return JsonResponse({"status": "ready"}, status=200)
    except Exception as e:
        return JsonResponse({"status": "not_ready", "error": str(e)[:200]}, status=503)
