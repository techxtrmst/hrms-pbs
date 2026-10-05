from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

urlpatterns = [
    path("login/", views.CustomLoginView.as_view(), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "change-password/",
        views.CustomPasswordChangeView.as_view(),
        name="change_password",
    ),
    # Password Reset / Activation
    path(
        "reset/<uidb64>/<token>/",
        views.CustomPasswordResetConfirmView.as_view(),
        name="password_reset_confirm",
    ),
    # Multi-account / multi-entity switcher endpoints
    path("link-account/", views.link_account_api, name="link_account_api"),
    path("switch/<int:user_id>/", views.switch_account_view, name="switch_account"),
    path("remove-linked/<int:user_id>/", views.remove_linked_account_api, name="remove_linked_account_api"),
]
