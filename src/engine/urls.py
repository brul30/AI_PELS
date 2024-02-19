# urls.py

from django.urls import path
from . import views

urlpatterns = [
    # ... other paths
    path('search', views.search, name='search'),
    path('feedback',views.feedback),
    path('create_payment_intent',views.create_payment_intent),

]
