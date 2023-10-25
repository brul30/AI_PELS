from django.urls import path
from . import views

urlpatterns = [
 #   path('',views.get_Data),
    path('send_audio_to_speechsuper', views.send_audio_to_speechsuper),
]