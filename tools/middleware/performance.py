import time
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)

class PerformanceMiddleware(MiddlewareMixin):
    """Simple middleware that records request processing time and logs slow requests.

    To enable, add 'tools.middleware.performance.PerformanceMiddleware' to MIDDLEWARE.
    """
    def process_request(self, request):
        request._perf_start = time.time()

    def process_response(self, request, response):
        start = getattr(request, '_perf_start', None)
        if start is not None:
            elapsed = (time.time() - start) * 1000.0
            # attach header for diagnostics
            try:
                response['X-Perf-Time-ms'] = f"{elapsed:.2f}"
            except Exception:
                pass
            # log slow requests
            if elapsed > 500:  # ms
                logger.warning('Slow request', extra={
                    'path': getattr(request, 'path', None),
                    'method': getattr(request, 'method', None),
                    'time_ms': elapsed
                })
        return response
