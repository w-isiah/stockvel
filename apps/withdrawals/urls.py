# apps/withdrawals/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_withdrawals, name='list_withdrawals'),
    path('add/', views.add_withdrawal, name='add_withdrawal'),
    path('edit/<int:withdrawal_id>/', views.edit_withdrawal, name='edit_withdrawal'),
    path('delete/<int:withdrawal_id>/', views.delete_withdrawal, name='delete_withdrawal'),
    path('signatures/', views.list_withdrawals_signatures, name='list_withdrawals_signatures'),
    path('approve-multiple/', views.approve_multiple_withdrawals, name='approve_multiple_withdrawals'),
]