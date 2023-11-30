# urls.py

from django.urls import path
from . import views

urlpatterns = [
    # ... other paths
    path('feedback', views.feedback, name='feedback'),
    path('search', views.search, name='search'),
]
