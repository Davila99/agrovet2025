from django.urls import path, include

# Keep a short top-level URL shim that points to the API package. The
# real router is defined in `add.api.urls` per project conventions.
urlpatterns = [
    path('', include('add.api.urls')),
]
