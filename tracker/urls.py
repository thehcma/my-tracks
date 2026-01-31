"""URL routing for tracker app."""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from typing import List
from django.urls.resolvers import URLPattern, URLResolver
from .views import LocationViewSet, DeviceViewSet

router = DefaultRouter()
router.register(r'locations', LocationViewSet, basename='location')
router.register(r'devices', DeviceViewSet, basename='device')

urlpatterns: List[URLPattern | URLResolver] = [
    path('', include(router.urls)),
]
