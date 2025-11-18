
from django.contrib import admin
from django.urls import path,include
from django.http import HttpResponse
from django.views.generic import RedirectView
from rest_framework import permissions
from rest_framework.authtoken import views
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


schema_view = get_schema_view(
   openapi.Info(
      title="Mi API",
      default_version='v1',
      description="Documentación de mi API",
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', RedirectView.as_view(url='/admin/', permanent=True)),
   # Simple health endpoint to verify the Django server and routing quickly
   path('api/health/', lambda request: HttpResponse('ok')),
    path('api/profiles/', include('profiles.api.urls')),
    path('api/auth/', include('auth_app.api.urls')),
    path('api/chat/', include('chat.api.urls')), 
   # Mount media.api at /api/ so the router's 'media' prefix becomes /api/media/
   path('api/', include('media.api.urls')),
   # Mount add.api at /api/ so the router's 'adds' prefix becomes /api/adds/
   path('api/', include('add.api.urls')),
   # Foro app endpoints
   path('api/foro/', include('foro.urls')),
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]