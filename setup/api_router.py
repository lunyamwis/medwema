from __future__ import annotations

from rest_framework.routers import DefaultRouter

from billing.api import BillViewSet, PaymentViewSet
from emr.api import LabQueueViewSet, LabResultViewSet, LabTestViewSet, LabViewSet
from inventory.api import (
    ItemCategoryViewSet,
    LocationViewSet,
    PurchaseOrderViewSet,
    StockMovementViewSet,
    SupplierViewSet,
)
from inventory.views import ConsumptionViewSet, ItemViewSet, StockViewSet
from patient.api import ConsultationViewSet, DoctorViewSet, PatientViewSet, QueueViewSet
from prescription.api import PrescriptionViewSet
from specialists.api import (
    DebtCaseViewSet,
    EquipmentItemViewSet,
    ExternalLabRequestViewSet,
    HomeVisitViewSet,
    NursingNoteViewSet,
    ServiceCatalogViewSet,
    SonographyStudyViewSet,
    SpecialistProfileViewSet,
    SpecialistTaskViewSet,
    SupplyInvoiceViewSet,
)

router = DefaultRouter()

# ── Patient ────────────────────────────────────────────────────────────────────
router.register(r"patients", PatientViewSet, basename="api-patient")
router.register(r"doctors", DoctorViewSet, basename="api-doctor")
router.register(r"queues", QueueViewSet, basename="api-queue")
router.register(r"consultations", ConsultationViewSet, basename="api-consultation")

# ── Billing ────────────────────────────────────────────────────────────────────
router.register(r"bills", BillViewSet, basename="api-bill")
router.register(r"payments", PaymentViewSet, basename="api-payment")

# ── Lab / EMR ──────────────────────────────────────────────────────────────────
router.register(r"labs", LabViewSet, basename="api-lab")
router.register(r"lab-tests", LabTestViewSet, basename="api-labtest")
router.register(r"lab-results", LabResultViewSet, basename="api-labresult")
router.register(r"lab-queue", LabQueueViewSet, basename="api-labqueue")

# ── Inventory ──────────────────────────────────────────────────────────────────
router.register(r"items", ItemViewSet, basename="api-item")
router.register(r"stock", StockViewSet, basename="api-stock")
router.register(r"stock-movements", StockMovementViewSet, basename="api-stockmovement")
router.register(r"purchase-orders", PurchaseOrderViewSet, basename="api-po")
router.register(r"consumption", ConsumptionViewSet, basename="api-consumption")
router.register(r"item-categories", ItemCategoryViewSet, basename="api-itemcategory")
router.register(r"suppliers", SupplierViewSet, basename="api-supplier")
router.register(r"locations", LocationViewSet, basename="api-location")

# ── Prescriptions ──────────────────────────────────────────────────────────────
router.register(r"prescriptions", PrescriptionViewSet, basename="api-prescription")

# ── Specialists ────────────────────────────────────────────────────────────────
router.register(r"specialist-profiles", SpecialistProfileViewSet, basename="api-specialist-profile")
router.register(r"service-catalog", ServiceCatalogViewSet, basename="api-service-catalog")
router.register(r"specialist-tasks", SpecialistTaskViewSet, basename="api-specialist-task")
router.register(r"sonography-studies", SonographyStudyViewSet, basename="api-sonography")
router.register(r"nursing-notes", NursingNoteViewSet, basename="api-nursing-note")
router.register(r"external-lab-requests", ExternalLabRequestViewSet, basename="api-external-lab")
router.register(r"home-visits", HomeVisitViewSet, basename="api-homevisit")
router.register(r"supply-invoices", SupplyInvoiceViewSet, basename="api-supply-invoice")
router.register(r"debt-cases", DebtCaseViewSet, basename="api-debt-case")
router.register(r"equipment", EquipmentItemViewSet, basename="api-equipment")
