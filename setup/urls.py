"""
URL configuration for setup project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from setup.api_router import router as api_router

urlpatterns = [
    path('admin/', admin.site.urls),
    path("accounts/", include("allauth.urls")),
    path("patients/", include("patient.urls")),
    path("", include("home.urls")),
    path('emr/', include('emr.urls')),
    path('chat/', include('chat.urls')),
    path('select2/', include('django_select2.urls')),
    path('inventory/', include('inventory.urls')),
    path('billing/', include('billing.urls')),
    path('prescriptions/', include('prescription.urls')),
    path('webpush/', include('webpush.urls')),
    path('notifications/', include('notification.urls')),
    path("specialists/", include("specialists.urls")),
    path("profile/", include("authentication.urls")),
    path("settings/", include("clinicmanager.urls")),

    # ── REST API ────────────────────────────────────────────────────────────────
    path("api/v1/", include(api_router.urls)),

    # ── API Documentation ───────────────────────────────────────────────────────
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="api-schema"), name="api-swagger"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="api-schema"), name="api-redoc"),

] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
