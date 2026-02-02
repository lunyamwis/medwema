from django.shortcuts import render


def index(request):
    return render(request, "chat/index.html")


def room(request, room_name):
    template = "chat/room_embed.html" if request.GET.get("embed") else "chat/room.html"
    return render(request, template, {"room_name": room_name})
    