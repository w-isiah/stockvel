# apps/loans/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.list_loans, name='list_loans'),
    path('add/', views.add_loan, name='add_loan'),
    path('edit/<int:loan_id>/', views.edit_loan, name='edit_loan'),
    path('delete/<int:loan_id>/', views.delete_loan, name='delete_loan'),
    path('approve-multiple/', views.approve_multiple_loans, name='approve_multiple_loans'),
    # NEW PATH
    path('signatures/', views.list_loan_signatures, name='list_loan_signatures'),
]