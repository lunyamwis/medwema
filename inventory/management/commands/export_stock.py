# inventory/management/commands/export_stock.py
from django.core.management.base import BaseCommand
from inventory.models import Item
import csv

class Command(BaseCommand):
    help = "Export current stock levels to CSV"

    def add_arguments(self, parser):
        parser.add_argument('outfile', type=str)

    def handle(self, *args, **options):
        out = options['outfile']
        with open(out, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['sku','item','total_stock','reorder_level'])
            for item in Item.objects.all():
                writer.writerow([item.sku, item.name, item.total_stock(), item.reorder_level])
        self.stdout.write(self.style.SUCCESS(f'Wrote stock to {out}'))
