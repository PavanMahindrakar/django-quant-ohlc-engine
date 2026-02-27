# options/urls.py

from django.urls import path
from .views import option_chain_summary, option_strike_detail, option_chain_view
from .import views
urlpatterns = [
    path("api/chain/summary/", option_chain_summary),
    path("api/chain/strike/",option_strike_detail),
    path("", option_chain_view,name="option-chain"),
    path("set-baseline/<int:snapshot_id>/", views.set_day_baseline, name="set_day_baseline"),
]