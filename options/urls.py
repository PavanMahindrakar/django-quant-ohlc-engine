# options/urls.py

from django.urls import path
from .views import option_chain_summary, option_strike_detail

urlpatterns = [
    path("api/chain/summary/", option_chain_summary),
    path("api/chain/strike/",option_strike_detail),
]