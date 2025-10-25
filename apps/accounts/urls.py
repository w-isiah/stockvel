from django.urls import path
from . import views

urlpatterns = [
    path("", views.login_view, name="login"),   # will match /accounts/login/
    path("logout/", views.logout_view, name="logout"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("register_view/", views.register_view, name="register_view"),
    path("profile/", views.account_profile, name="profile"),
    path("edit_profile/", views.edit_profile, name="edit_profile"),
    path('users_list/', views.list_users, name='users_list'),
    path("users/edit/<int:user_id>/", views.user_edit, name="user_edit"),
    path("users/delete/<int:user_id>/", views.delete_user, name="delete_user"),
]



