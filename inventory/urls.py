# inventory/urls.py
from django.urls import path
from . import views

from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'items', views.ItemViewSet, basename='items')
router.register(r'stock', views.StockViewSet, basename='stock')
router.register(r'consumptions', views.ConsumptionViewSet, basename='consumptions')
urlpatterns = router.urls

urlpatterns += [
    path('', views.dashboard, name='inventory_dashboard'),
    path('items/', views.item_list, name='item_list'),
    path('items/<int:pk>/', views.item_detail, name='item_detail'),
    path('po/create/', views.create_po, name='po_create'),
    path('po/', views.po_list, name='po_list'),
    path('po/<int:pk>/receive/', views.receive_po, name='po_receive'),
    path('movement/create/', views.stock_movement_create, name='movement_create'),
    path('consume/', views.consume_item, name='consume_item'),
]
