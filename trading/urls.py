# config/trading/urls.py

from django.urls import path
from . import views

urlpatterns = [

    # -------------------------------
    # Institutional Configuration UI
    # -------------------------------
    path("config/", views.config_panel, name="config_panel"),
    path("config/<int:pk>/edit/", views.config_panel, name="config_edit"),

    # -------------------------------
    # Dashboard UI
    # -------------------------------
    path("dashboard/", views.dashboard_page, name="dashboard"),

    # -------------------------------
    # Engine API
    # -------------------------------
    path("api/engine/run/", views.engine_run_api, name="engine_run_api"),

    # -------------------------------
    # Signal Monitoring
    # -------------------------------
    path("signals/logs/", views.signal_history_page, name="signal_logs"),
]