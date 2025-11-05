from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from inventory.models import PurchaseOrder, StockMovement, Item

class Command(BaseCommand):
    help = 'Create default inventory groups and permissions'

    def handle(self, *args, **options):
        # Create groups
        tech_group, _ = Group.objects.get_or_create(name='Lab Technician')
        pharmacist_group, _ = Group.objects.get_or_create(name='Pharmacist')
        inventory_mgr_group, _ = Group.objects.get_or_create(name='Inventory Manager')

        # Give inventory manager all perms for inventory models
        models = [PurchaseOrder, StockMovement, Item]
        for m in models:
            ct = ContentType.objects.get_for_model(m)
            perms = Permission.objects.filter(content_type=ct)
            for p in perms:
                inventory_mgr_group.permissions.add(p)
        self.stdout.write(self.style.SUCCESS('Groups and permissions created.'))
