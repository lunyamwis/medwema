from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .utils import generate_vapid_keypair  # wherever your function is



import json
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from webpush.forms import SubscriptionForm, WebPushForm
from django.contrib.auth import get_user_model

User = get_user_model()


@login_required
def get_or_generate_vapid_keys(request):
    """
    Always use VAPID keys belonging to the superuser.
    If missing, generate new ones and store them only for the superuser.
    """

    # Get the superuser (assuming only one)
    try:
        admin = User.objects.filter(is_superuser=True).first()
    except User.DoesNotExist:
        return JsonResponse({"error": "No superuser exists"}, status=500)

    if admin is None:
        return JsonResponse({"error": "No superuser exists"}, status=500)

    # Check if admin already has keys
    if not admin.vapid_public_key or not admin.vapid_private_key:
        public, private = generate_vapid_keypair()
        admin.vapid_public_key = public
        admin.vapid_private_key = private
        admin.save()
        print("🔑 Generated NEW VAPID keys for superuser")

    # Return the superuser's keys
    return JsonResponse({
        "public_key": admin.vapid_public_key,
        "private_key":admin.vapid_private_key
    })



@require_POST
@csrf_exempt
def save_info(request):
    """
    Save or update push subscription info for the authenticated user or group.
    Expects JSON payload:
    {
        "endpoint": "...",
        "keys": {"p256dh": "...", "auth": "..."},
        "status_type": "subscribe",  # or "unsubscribe"
        "group": null
    }
    """

    try:
        data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    status_type = data.get("status_type")
    if status_type not in ["subscribe", "unsubscribe"]:
        return JsonResponse({"error": "Invalid status_type"}, status=400)

    group_name = data.get("group")
    print("we are here")

    # Use django_webpush forms
    subscription_form = SubscriptionForm(data)
    web_push_form = WebPushForm(data)

    if not subscription_form.is_valid():
        return JsonResponse({
            "error": "Invalid subscription data",
            "details": subscription_form.errors
        }, status=400)

    if not web_push_form.is_valid():
        return JsonResponse({
            "error": "Invalid web push data",
            "details": web_push_form.errors
        }, status=400)

    # Only save if user authenticated or group provided
    if not request.user.is_authenticated and not group_name:
        return JsonResponse({"error": "User not authenticated and group missing"}, status=403)

    subscription = subscription_form.get_or_save()
    web_push_form.save_or_delete(
        subscription=subscription,
        user=request.user if request.user.is_authenticated else None,
        status_type=status_type,
        group_name=group_name
    )

    return JsonResponse(
        {"success": True, "status_type": status_type},
        status=201 if status_type == "subscribe" else 202
    )
