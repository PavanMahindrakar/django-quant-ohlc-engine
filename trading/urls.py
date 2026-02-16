# config/trading/urls.py
from django.urls import path
from . import views

urlpatterns = [

    # CRUD
    path("", views.stock_list, name="stock_list"),
    path("create/", views.stock_create, name="stock_create"),
    path("<int:pk>/edit/", views.stock_update, name="stock_update"),
    path("<int:pk>/delete/", views.stock_delete, name="stock_delete"),

    # Dashboard UI
    path("dashboard/", views.dashboard_page, name="dashboard"),

    # Engine API
    path("api/engine/run/", views.engine_run_api, name="engine_run_api"),
]