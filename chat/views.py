from django.shortcuts import render

ROOMS = {
    "laboratory": {"icon": "bi-eyedropper", "color": "#6f42c1", "desc": "Lab results, tests & analysis"},
    "doctors":    {"icon": "bi-heart-pulse-fill", "color": "#0d6efd", "desc": "Clinical discussions & consults"},
    "operations": {"icon": "bi-gear-wide-connected", "color": "#fd7e14", "desc": "Admin, ops & logistics"},
    "general":    {"icon": "bi-chat-dots-fill", "color": "#198754", "desc": "General team conversation"},
}


def index(request):
    return render(request, "chat/index.html", {"rooms": ROOMS})


def room(request, room_name):
    meta = ROOMS.get(room_name, {"icon": "bi-chat-fill", "color": "#6c757d", "desc": ""})
    ctx = {
        "room_name": room_name,
        "room_meta": meta,
        "rooms": ROOMS,
        "username": request.user.get_full_name().strip() or request.user.username,
    }
    template = "chat/room_embed.html" if request.GET.get("embed") else "chat/room.html"
    return render(request, template, ctx)
