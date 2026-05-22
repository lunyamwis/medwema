from django.urls import path

from home import views

urlpatterns = [
    path("", views.index, name="index"),
    path("blog/", views.blog_list, name="blog_list"),
    path("blog/<slug:slug>/", views.blog_detail, name="blog_detail"),
    path("subscribe/", views.subscribe, name="subscribe"),
]
