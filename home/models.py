from __future__ import annotations

from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class BlogCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, max_length=120)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Blog categories"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class BlogPost(models.Model):
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, max_length=280)
    excerpt = models.TextField(max_length=500, help_text="Short summary shown in listings.")
    content = models.TextField(help_text="Main post body. HTML is supported.")
    featured_image = models.ImageField(upload_to="blog/", null=True, blank=True)
    author = models.ForeignKey(
        "authentication.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="blog_posts",
    )
    category = models.ForeignKey(
        BlogCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
    )
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    views_count = models.PositiveIntegerField(default=0, editable=False)

    class Meta:
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        if self.is_published and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)

    @property
    def read_time(self):
        return max(1, round(len(self.content.split()) / 200))


class Subscriber(models.Model):
    SOURCE_CHOICES = [
        ("landing", "Landing Page"),
        ("blog", "Blog"),
        ("other", "Other"),
    ]

    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, blank=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="landing")

    class Meta:
        ordering = ["-subscribed_at"]

    def __str__(self):
        return self.email
