from django.urls import path
from . import views

urlpatterns = [
 #   path('',views.get_Data),
    path('signup', views.signup),
    path('login', views.login),
    path('test_token', views.test_token),
]