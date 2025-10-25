# apps/investments/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_investments, name='list_investments'),
    path('add/', views.add_investment, name='add_investment'),
    path('edit/<int:investment_id>/', views.edit_investment, name='edit_investment'),
    path('approve_multiple/', views.approve_multiple_investments, name='approve_multiple_investments'),
    path('signatures/', views.list_investment_signatures, name='list_investment_signatures'),
]