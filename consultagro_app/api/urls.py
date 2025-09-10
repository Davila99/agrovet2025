from django.urls import path
from .views import RegisterView, LoginView, VeterinaryList, AgronomoList

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("veterinarios/", VeterinaryList.as_view(), name="veterinarios"),
    path("agronomos/", AgronomoList.as_view(), name="agronomos"),
]
