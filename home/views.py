from __future__ import annotations

import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from home.models import BlogCategory, BlogPost, Subscriber


def index(request):
    blog_posts = (
        BlogPost.objects.filter(is_published=True)
        .select_related("author", "category")[:3]
    )
    return render(request, "index.html", {"blog_posts": blog_posts})


def blog_list(request):
    category_slug = request.GET.get("category", "")
    categories = BlogCategory.objects.all()
    posts = BlogPost.objects.filter(is_published=True).select_related("author", "category")
    active_category = None
    if category_slug:
        active_category = get_object_or_404(BlogCategory, slug=category_slug)
        posts = posts.filter(category=active_category)
    return render(request, "home/blog_list.html", {
        "posts": posts,
        "categories": categories,
        "active_category": active_category,
    })


def blog_detail(request, slug):
    post = get_object_or_404(BlogPost, slug=slug, is_published=True)
    BlogPost.objects.filter(pk=post.pk).update(views_count=post.views_count + 1)
    related = (
        BlogPost.objects.filter(is_published=True)
        .exclude(pk=post.pk)
        .select_related("author", "category")[:3]
    )
    if post.category:
        related = (
            BlogPost.objects.filter(is_published=True, category=post.category)
            .exclude(pk=post.pk)
            .select_related("author", "category")[:3]
        )
    return render(request, "home/blog_detail.html", {"post": post, "related": related})


@require_POST
def subscribe(request):
    try:
        data = json.loads(request.body)
        email = data.get("email", "").strip()
        name = data.get("name", "").strip()
    except (json.JSONDecodeError, AttributeError):
        email = request.POST.get("email", "").strip()
        name = request.POST.get("name", "").strip()

    if not email:
        return JsonResponse({"success": False, "error": "Email address is required."})

    subscriber, created = Subscriber.objects.get_or_create(
        email=email,
        defaults={"name": name, "source": "landing"},
    )
    if not created:
        if not subscriber.is_active:
            subscriber.is_active = True
            subscriber.save(update_fields=["is_active"])
            return JsonResponse({"success": True, "message": "Welcome back! You're re-subscribed."})
        return JsonResponse({"success": False, "error": "This email is already subscribed."})

    return JsonResponse({"success": True, "message": "Thank you for subscribing!"})
