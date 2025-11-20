from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterViewSet, LoginViewSet, UploadProfilePictureView, UserView,
    request_password_reset_by_phone, verify_code_and_reset_password, test_token_view
)

router = DefaultRouter()
router.register(r'register', RegisterViewSet, basename='register')
router.register(r'login', LoginViewSet, basename='login')
router.register(r'users', UserView, basename='user')

urlpatterns = [
    path('', include(router.urls)),
    path('upload-profile-picture/', UploadProfilePictureView.as_view(), name='upload-profile-picture'),
    path('password-reset/request/', request_password_reset_by_phone, name='password-reset-request'),
    path('password-reset/request-phone/', request_password_reset_by_phone, name='password-reset-request-phone'),
    path('password-reset/verify/', verify_code_and_reset_password, name='password-reset-verify'),
    path('password-reset/verify-phone/', verify_code_and_reset_password, name='password-reset-verify-phone'),
    path('test-token/', test_token_view, name='test-token'),
]

