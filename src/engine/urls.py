# urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('search', views.search, name='search'),
    path('process_audio', views.process_audio, name='process_audio'),
    path('generate_feedback', views.generate_feedback, name='generate_feedback'),
    path('test_feedback', views.test_feedback, name='test_feedback')
]
