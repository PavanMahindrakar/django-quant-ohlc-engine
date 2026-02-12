# config/trading/urls.py
from django.urls import path
from . import views
from .views import generate_signals


urlpatterns = [
    path("", views.stock_list, name="stock_list"),
    path("create/", views.stock_create, name="stock_create"),
    path("<int:pk>/edit/", views.stock_update, name="stock_update"),
    path("<int:pk>/delete/", views.stock_delete, name="stock_delete"),
    path("signals/", generate_signals, name="generate_signals"),
    path("api/signals/<str:symbol_token>/", views.api_signal_debug, name="api_signal_debug"),

]
