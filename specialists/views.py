from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from patient.models import Patient, Consultation, Queue
from billing.models import Bill

from .forms import (
    SpecialistTaskForm, SonographyStudyForm, NursingNoteForm,
    ExternalLabRequestForm, ExternalLabResultForm,
    HomeVisitForm, SupplyInvoiceForm, EquipmentItemForm, DebtFollowUpForm
)
from django.db import models
from .models import (
    NotificationForSpecialist, SpecialistTask, SonographyStudy, NursingNote,
    ExternalLabRequest, ExternalLabResult, HomeVisit, SupplyInvoice,
    DebtCase, EquipmentItem
)
from .services import notify_user, bill_for_service, send_external_lab_email


def _clinic_from_request(request):
    # Adapt this to your tenancy pattern: request.user.clinic / request.clinic / etc.
    # For now: try a common pattern
    return request.user.clinics.last()

@login_required
def dashboard(request):
    clinic = _clinic_from_request(request)
    my_notifications = NotificationForSpecialist.objects.filter(clinic=clinic, recipient=request.user).order_by("-created_at")[:10]

    ctx = {
        "clinic": clinic,
        "notif": my_notifications,
        "counts": {
            "tasks_waiting": SpecialistTask.objects.filter(clinic=clinic, status="waiting").count(),
            "sonography_today": SonographyStudy.objects.filter(clinic=clinic, performed_at__date=timezone.now().date()).count(),
            "nursing_today": NursingNote.objects.filter(clinic=clinic, created_at__date=timezone.now().date()).count(),
            "external_pending": ExternalLabRequest.objects.filter(clinic=clinic).exclude(status__in=["received", "closed"]).count(),
            "debts_open": DebtCase.objects.filter(clinic=clinic, status__in=["open", "promised"]).count(),
            "low_stock": EquipmentItem.objects.filter(clinic=clinic, qty_available__lte=models.F("reorder_level")).count() if clinic else 0,
        }
    }
    ctx["task_list_url"] = reverse("specialists:task_list")
    ctx["sonography_url"] = reverse("specialists:sonography_create")
    ctx["nursing_url"] = reverse("specialists:nursing_create")
    ctx["external_lab_url"] = reverse("specialists:external_lab_list")

    return render(request, "specialists/dashboard.html", ctx)


# ---------------- Specialist Tasks (Specialists Area) ----------------

@login_required
def task_list(request):
    clinic = _clinic_from_request(request)
    qs = SpecialistTask.objects.filter(clinic=clinic).order_by("-created_at")
    role = request.GET.get("role")
    status = request.GET.get("status")
    if role:
        qs = qs.filter(role=role)
    if status:
        qs = qs.filter(status=status)
    return render(request, "specialists/specialist/task_list.html", {"tasks": qs})


@login_required
def task_create(request):
    clinic = _clinic_from_request(request)
    form = SpecialistTaskForm(request.POST or None)
    # import pdb;pdb.set_trace()
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.clinic = clinic
        obj.save()
        messages.success(request, "Task created.")
        return redirect("specialists:task_list")

    return render(request, "specialists/specialist/task_form.html", {"form": form})


@login_required
def task_bill_service(request, task_id):
    """
    One-click: select service already set on task, generate bill item.
    """
    clinic = _clinic_from_request(request)
    task = get_object_or_404(SpecialistTask, clinic=clinic, id=task_id)

    if not task.service:
        messages.error(request, "Set a service on the task first.")
        return redirect("specialists:task_list")

    bill, _item = bill_for_service(
        clinic=clinic,
        patient=task.patient,
        consultation=task.consultation,
        service=task.service,
        created_by=request.user,
    )
    task.bill = bill
    task.save()

    messages.success(request, f"Billing added to Bill #{bill.id}.")
    return redirect("specialists:task_list")


# ---------------- Alerts: patient arrived ----------------

@login_required
def patient_arrived_alert(request, queue_id):
    """
    Trigger when reception marks patient as arrived / moved to specialist area.
    Alerts doctor + specialist + patient (if you later add SMS/email to patient).
    """
    clinic = _clinic_from_request(request)
    q = get_object_or_404(Queue, clinic=clinic, id=queue_id)

    # notify doctor
    if q.doctor_id:
        notify_user(
            clinic=clinic,
            recipient=q.doctor.user if hasattr(q.doctor, "user") else request.user,
            title="Patient arrived",
            message=f"{q.patient.name} has arrived and is waiting in queue #{q.queue_number}.",
            url=reverse("specialists:dashboard"),
        )

    # notify any waiting specialist tasks for this patient
    tasks = SpecialistTask.objects.filter(clinic=clinic, patient=q.patient, status="waiting")
    for t in tasks:
        if t.assigned_to:
            notify_user(
                clinic=clinic,
                recipient=t.assigned_to,
                title="Patient arrived for your service",
                message=f"{q.patient.name} has arrived. Task: {t.role}.",
                url=reverse("specialists:task_list"),
            )

    messages.success(request, "Alerts sent.")
    return redirect("specialists:dashboard")


# ---------------- Sonography ----------------

@login_required
def sonography_list(request):
    clinic = _clinic_from_request(request)
    qs = SonographyStudy.objects.filter(clinic=clinic).order_by("-performed_at")
    return render(request, "specialists/sonography/list.html", {"rows": qs})


@login_required
def sonography_create(request):
    clinic = _clinic_from_request(request)
    form = SonographyStudyForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form = SonographyStudyForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.clinic = clinic
            obj.performed_by = request.user
            obj.save()
            messages.success(request, "Sonography report saved.")
            return redirect("specialists:sonography_list")
    else:
        form = SonographyStudyForm()
    return render(request, "specialists/sonography/form.html", {"form": form})


@login_required
def sonography_detail(request, pk):
    clinic = _clinic_from_request(request)
    obj = get_object_or_404(SonographyStudy, clinic=clinic, pk=pk)
    return render(request, "specialists/sonography/detail.html", {"obj": obj})


# ---------------- Nursing / Observation ----------------

@login_required
def nursing_list(request):
    clinic = _clinic_from_request(request)
    qs = NursingNote.objects.filter(clinic=clinic).order_by("-created_at")
    return render(request, "specialists/nursing/list.html", {"rows": qs})


@login_required
def nursing_create(request):
    clinic = _clinic_from_request(request)
    if request.method == "POST":
        form = NursingNoteForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.clinic = clinic
            obj.created_by = request.user
            obj.save()
            messages.success(request, "Nursing note saved.")
            return redirect("specialists:nursing_list")
    else:
        form = NursingNoteForm()
    return render(request, "specialists/nursing/form.html", {"form": form})


@login_required
def nursing_detail(request, pk):
    clinic = _clinic_from_request(request)
    obj = get_object_or_404(NursingNote, clinic=clinic, pk=pk)
    return render(request, "specialists/nursing/detail.html", {"obj": obj})


# ---------------- External lab request ----------------

@login_required
def external_lab_list(request):
    clinic = _clinic_from_request(request)
    qs = ExternalLabRequest.objects.filter(clinic=clinic).order_by("-created_at")
    return render(request, "specialists/external_lab/request_list.html", {"rows": qs})


@login_required
def external_lab_create(request):
    clinic = _clinic_from_request(request)
    form = ExternalLabRequestForm(request.POST or None) 
    # import pdb;pdb.set_trace()
    if request.method == "POST" and form.is_valid():
        form = ExternalLabRequestForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.clinic = clinic
            obj.created_by = request.user
            obj.save()
            messages.success(request, "External lab request created (draft).")
            return redirect("specialists:external_lab_detail", pk=obj.pk)
    else:
        form = ExternalLabRequestForm()
    return render(request, "specialists/external_lab/request_form.html", {"form": form})


@login_required
def external_lab_detail(request, pk):
    clinic = _clinic_from_request(request)
    obj = get_object_or_404(ExternalLabRequest, clinic=clinic, pk=pk)
    upload_form = ExternalLabResultForm()
    return render(request, "specialists/external_lab/request_detail.html", {"obj": obj, "upload_form": upload_form})


@login_required
def external_lab_send(request, pk):
    clinic = _clinic_from_request(request)
    obj = get_object_or_404(ExternalLabRequest, clinic=clinic, pk=pk)
    send_external_lab_email(obj)
    messages.success(request, "Email sent to external lab.")
    return redirect("specialists:external_lab_detail", pk=pk)


@login_required
def external_lab_upload_result(request, pk):
    clinic = _clinic_from_request(request)
    req_obj = get_object_or_404(ExternalLabRequest, clinic=clinic, pk=pk)
    if request.method == "POST":
        form = ExternalLabResultForm(request.POST, request.FILES)
        if form.is_valid():
            res = form.save(commit=False)
            res.request = req_obj
            res.uploaded_by = request.user
            res.save()
            req_obj.status = "received"
            req_obj.save()
            messages.success(request, "External lab result uploaded.")
    return redirect("specialists:external_lab_detail", pk=pk)


# ---------------- Home visits ----------------

@login_required
def home_visit_list(request):
    clinic = _clinic_from_request(request)
    qs = HomeVisit.objects.filter(clinic=clinic).order_by("-visit_date")
    return render(request, "specialists/home_visit/list.html", {"rows": qs})


@login_required
def home_visit_create(request):
    clinic = _clinic_from_request(request)
    if request.method == "POST":
        form = HomeVisitForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.clinic = clinic
            obj.save()
            messages.success(request, "Home visit saved.")
            return redirect("specialists:home_visit_list")
    else:
        form = HomeVisitForm()
    return render(request, "specialists/home_visit/form.html", {"form": form})


# ---------------- Supplies invoicing ----------------

@login_required
def supply_invoice_list(request):
    clinic = _clinic_from_request(request)
    qs = SupplyInvoice.objects.filter(clinic=clinic).order_by("-invoice_date")
    return render(request, "specialists/supplies/invoice_list.html", {"rows": qs})


@login_required
def supply_invoice_create(request):
    clinic = _clinic_from_request(request)
    if request.method == "POST":
        form = SupplyInvoiceForm(request.POST, request.FILES)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.clinic = clinic
            obj.created_by = request.user
            obj.save()
            messages.success(request, "Supply invoice recorded.")
            return redirect("specialists:supply_invoice_list")
    else:
        form = SupplyInvoiceForm()
    return render(request, "specialists/supplies/invoice_form.html", {"form": form})


# ---------------- Debts ----------------

@login_required
def debts_list(request):
    clinic = _clinic_from_request(request)
    qs = DebtCase.objects.filter(clinic=clinic).select_related("bill", "patient").order_by("-created_at")
    return render(request, "specialists/debts/list.html", {"rows": qs})


@login_required
def debt_detail(request, pk):
    clinic = _clinic_from_request(request)
    obj = get_object_or_404(DebtCase, clinic=clinic, pk=pk)
    follow_form = DebtFollowUpForm()
    # WhatsApp quick link (no sending, just generates a message link)
    phone = obj.patient.phone_number
    wa_link = None
    if phone:
        msg = f"Hello {obj.patient.name}, your bill #{obj.bill.id} is pending. Amount: {obj.balance}. Kindly pay to proceed. Thank you."
        wa_link = f"https://wa.me/{phone}?text={msg.replace(' ', '%20')}"
    return render(request, "specialists/debts/detail.html", {"obj": obj, "follow_form": follow_form, "wa_link": wa_link})


@login_required
def debt_add_followup(request, pk):
    clinic = _clinic_from_request(request)
    obj = get_object_or_404(DebtCase, clinic=clinic, pk=pk)
    if request.method == "POST":
        form = DebtFollowUpForm(request.POST)
        if form.is_valid():
            fu = form.save(commit=False)
            fu.debt_case = obj
            fu.created_by = request.user
            fu.save()
            messages.success(request, "Follow-up logged.")
    return redirect("specialists:debt_detail", pk=pk)


# ---------------- Equipment list ----------------

@login_required
def equipment_list(request):
    clinic = _clinic_from_request(request)
    qs = EquipmentItem.objects.filter(clinic=clinic).order_by("name")
    return render(request, "specialists/equipment/list.html", {"rows": qs})


@login_required
def equipment_create(request):
    clinic = _clinic_from_request(request)
    if request.method == "POST":
        form = EquipmentItemForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.clinic = clinic
            obj.save()
            messages.success(request, "Equipment item added.")
            return redirect("specialists:equipment_list")
    else:
        form = EquipmentItemForm()
    return render(request, "specialists/equipment/form.html", {"form": form})
