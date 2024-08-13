from django.urls import path, re_path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("home/", views.index, name="home"),
    re_path(r'^download/(?P<video_id>[a-zA-Z0-9_-]{11})/$', views.download, name='download'),
    path('dl/', views.handle_download, name='dl'),
    re_path(r'^media/(?P<video_id>[a-zA-Z0-9_-]{11})\.(?P<extension>mp3|mp4)$', views.serve_media_file, name='media'),
    path('privacy/', views.privacy, name='privacy'),
    path('dmca/', views.dmca, name='dmca'),
]
