"""Named routes for the Lite edition."""

from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("campaigns/", views.campaigns, name="campaigns"),
    path("campaigns/new/", views.campaign_create, name="campaign_create"),
    path("campaigns/<int:pk>/toggle/", views.campaign_toggle, name="campaign_toggle"),
    path("sites/", views.sites, name="sites"),
    path("sites/new/", views.site_create, name="site_create"),
    path("sites/<int:pk>/toggle/", views.site_toggle, name="site_toggle"),
    path("people/", views.people, name="people"),
    path("people/new/", views.distributor_create, name="distributor_create"),
    path("assignments/", views.assignments, name="assignments"),
    path("assignments/new/", views.assignment_create, name="assignment_create"),
    path("assignments/<int:pk>/toggle/", views.assignment_toggle, name="assignment_toggle"),
    path("inventory/", views.inventory, name="inventory"),
    path("inventory/receipt/", views.receipt_create, name="receipt_create"),
    path("inventory/allocation/", views.allocation_create, name="allocation_create"),
    path("deliveries/", views.deliveries, name="deliveries"),
    path("deliveries/new/", views.delivery_create, name="delivery_create"),
    path("deliveries/<int:pk>/", views.delivery_detail, name="delivery_detail"),
    path("deliveries/<int:pk>/review/", views.delivery_review, name="delivery_review"),
    path("deliveries/<int:pk>/photo/", views.delivery_photo, name="delivery_photo"),
    path("activity/", views.activity, name="activity"),
]
