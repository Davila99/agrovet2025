"""
URL configuration for marketplace-service.
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
import sys
import os

# Add common directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from common.health.views import health, health_detailed

schema_view = get_schema_view(
   openapi.Info(
      title="Marketplace Service API",
      default_version='v1',
      description="API para gestión de anuncios y marketplace",
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health, name='health'),
    path('health/detailed/', health_detailed, name='health_detailed'),
    path('api/', include('add.api.urls')),
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

