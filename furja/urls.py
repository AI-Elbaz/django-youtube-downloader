"""
URL configuration for furja project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
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
from django.contrib.sitemaps.views import sitemap, index
from ytdown.sitemaps import VideoSitemap

from django.conf import settings
from django.conf.urls.static import static

sitemaps = {"videos": VideoSitemap}

urlpatterns = ([
    path('admin/', admin.site.urls),
    path('', include('ytdown.urls')),
    path(
        "sitemap.xml",
        index,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.index"
    ),
    path(
        "<section>.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap"
    ),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
)