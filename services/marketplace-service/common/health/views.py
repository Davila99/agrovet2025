"""
Health check endpoint for all microservices.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import logging

logger = logging.getLogger(__name__)


@require_http_methods(["GET"])
def health(request):
    """
    Simple health check endpoint.
    Returns 200 OK if service is running.
    """
    return JsonResponse({
        "status": "ok",
        "service": "microservice"
    })


@require_http_methods(["GET"])
def health_detailed(request):
    """
    Detailed health check including database and Redis connectivity.
    """
    from django.db import connection
    from django.core.cache import cache
    
    status = {
        "status": "ok",
        "service": "microservice",
        "checks": {}
    }
    
    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        status["checks"]["database"] = "ok"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        status["checks"]["database"] = f"error: {str(e)}"
        status["status"] = "degraded"
    
    # Check Redis cache
    try:
        cache.set("health_check", "ok", 10)
        cache.get("health_check")
        status["checks"]["redis"] = "ok"
    except Exception as e:
        logger.error(f"Redis health check failed: {e}")
        status["checks"]["redis"] = f"error: {str(e)}"
        status["status"] = "degraded"
    
    response_code = 200 if status["status"] == "ok" else 503
    return JsonResponse(status, status=response_code)

