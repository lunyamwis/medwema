from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html

from home.models import BlogCategory, BlogPost, Subscriber


@admin.register(BlogCategory)
class BlogCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "post_count")
    search_fields = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    @admin.display(description="Posts")
    def post_count(self, obj):
        return obj.posts.filter(is_published=True).count()


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = (
        "title", "author", "category", "is_published",
        "published_at", "views_count", "read_time_display",
    )
    list_filter = ("is_published", "category", "author", "created_at")
    search_fields = ("title", "excerpt", "content")
    prepopulated_fields = {"slug": ("title",)}
    date_hierarchy = "published_at"
    list_editable = ("is_published",)
    readonly_fields = ("views_count", "created_at", "updated_at")
    ordering = ("-created_at",)
    list_select_related = ("author", "category")
    fieldsets = (
        (None, {"fields": ("title", "slug", "excerpt", "content", "featured_image")}),
        ("Classification", {"fields": ("author", "category")}),
        ("Publishing", {"fields": ("is_published", "published_at")}),
        ("Stats", {"fields": ("views_count", "created_at", "updated_at"), "classes": ("collapse",)}),
    )

    @admin.display(description="Read time")
    def read_time_display(self, obj):
        return f"{obj.read_time} min"


@admin.register(Subscriber)
class SubscriberAdmin(admin.ModelAdmin):
    list_display = ("email", "name", "source", "subscribed_at", "is_active", "status_badge")
    list_filter = ("is_active", "source", "subscribed_at")
    search_fields = ("email", "name")
    date_hierarchy = "subscribed_at"
    list_editable = ("is_active",)
    ordering = ("-subscribed_at",)
    readonly_fields = ("subscribed_at",)
    actions = ["activate_subscribers", "deactivate_subscribers"]

    from django.utils.html import format_html

    @admin.display(description="Status")
    def status_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span style="color:{};font-weight:{};">● {}</span>',
                "#16a34a",
                "600",
                "Active"
            )

        return format_html(
            '<span style="color:{};font-weight:{};">● {}</span>',
            "#dc2626",
            "600",
            "Inactive"
        )

    @admin.action(description="Activate selected subscribers")
    def activate_subscribers(self, request, queryset):
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} subscriber(s) activated.")

    @admin.action(description="Deactivate selected subscribers")
    def deactivate_subscribers(self, request, queryset):
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} subscriber(s) deactivated.")
