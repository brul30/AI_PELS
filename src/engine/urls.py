# urls.py

from django.urls import path
from . import views

urlpatterns = [
    # ... other paths
    path('search', views.search, name='search'),
    path('feedback',views.feedback),

]
