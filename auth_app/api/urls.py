from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RegisterViewSet, LoginViewSet, UploadProfilePictureView, UserView

router = DefaultRouter()
router.register(r'register', RegisterViewSet, basename='register')
router.register(r'login', LoginViewSet, basename='login')
router.register(r'users', UserView, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path('upload-profile-picture/', UploadProfilePictureView.as_view(), name='upload-profile-picture'),
]

