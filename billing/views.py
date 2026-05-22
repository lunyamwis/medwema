from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib import messages
from django.core.paginator import Paginator

logger = logging.getLogger(__name__)
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import requests as http_requests

from billing.models import Bill, Payment
from billing.services import payment_mark_manual, revenue_in_range
from billing.forms import BillEditForm
from billing.utils import get_last_n_subaccount_transactions, get_transaction_by_reference

PAYSTACK_BASE_URL = "https://api.paystack.co"


def _get_clinic(user):
    return user.clinics.select_related().last()


# ─── Dashboard ───────────────────────────────────────────────────────────────

@login_required
def billing_dashboard(request):
    clinic = _get_clinic(request.user)
    today = timezone.localdate()
    week_start = today - timedelta(days=today.weekday())

    base_qs = Bill.objects.filter(clinic=clinic)

    unpaid_count = base_qs.filter(is_paid=False).count()
    paid_today_count = base_qs.filter(is_paid=True, updated_at__date=today).count()

    revenue_today = (
        Payment.objects.filter(
            bill__clinic=clinic,
            status__in=["success", "manual"],
            paid_at__date=today,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    revenue_week = (
        Payment.objects.filter(
            bill__clinic=clinic,
            status__in=["success", "manual"],
            paid_at__date__gte=week_start,
        ).aggregate(total=Sum("amount"))["total"]
        or Decimal("0.00")
    )

    recent_bills = (
        base_qs
        .select_related("patient", "consultation")
        .order_by("-created_at")[:10]
    )

    return render(
        request,
        "billing/dashboard.html",
        {
            "unpaid_count": unpaid_count,
            "paid_today_count": paid_today_count,
            "revenue_today": revenue_today,
            "revenue_week": revenue_week,
            "recent_bills": recent_bills,
        },
    )


# ─── Bill List ────────────────────────────────────────────────────────────────

@login_required
def billing_list(request):
    clinic = _get_clinic(request.user)
    q = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "")

    bills = (
        Bill.objects.filter(clinic=clinic)
        .select_related("patient", "consultation")
        .order_by("-created_at")
    )

    if q:
        bills = bills.filter(patient__name__icontains=q)

    if status_filter == "paid":
        bills = bills.filter(is_paid=True)
    elif status_filter == "unpaid":
        bills = bills.filter(is_paid=False)

    paginator = Paginator(bills, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "billing/billing_list.html",
        {
            "page_obj": page_obj,
            "query": q,
            "status_filter": status_filter,
        },
    )


# ─── Bill Detail ──────────────────────────────────────────────────────────────

@login_required
def bill_detail(request, pk):
    bill = get_object_or_404(
        Bill.objects.select_related("patient", "consultation", "clinic")
        .prefetch_related("items", "payments"),
        pk=pk,
    )
    return render(request, "billing/bill_detail.html", {"bill": bill})


# ─── Bill Edit ────────────────────────────────────────────────────────────────

@login_required
def bill_edit(request, pk):
    bill = get_object_or_404(Bill, pk=pk)

    if bill.is_paid:
        logger.warning("Attempt to edit paid bill #%s by %s", bill.id, request.user.username)
        messages.error(request, "You cannot edit a bill that has already been paid.")
        return redirect("bill_detail", pk=pk)

    if request.method == "POST":
        form = BillEditForm(request.POST, instance=bill)
        if form.is_valid():
            form.save()
            logger.info("Bill #%s updated by %s", bill.id, request.user.username)
            messages.success(request, f"Bill #{bill.id} updated successfully.")
            return redirect("bill_detail", pk=pk)
        else:
            logger.warning("Bill #%s edit form invalid for %s: %s", bill.id, request.user.username, form.errors)
            messages.error(request, "Please correct the errors below.")
    else:
        form = BillEditForm(instance=bill)

    return render(request, "billing/bill_edit.html", {"bill": bill, "form": form})


# ─── Mark Bill Paid ───────────────────────────────────────────────────────────

@login_required
@require_POST
def mark_bill_paid(request, pk):
    bill = get_object_or_404(Bill, pk=pk)
    payment_method = request.POST.get("payment_method", "CASH")

    payment_mark_manual(
        bill=bill,
        amount=bill.net_amount,
        created_by=request.user,
        payment_method=payment_method,
    )

    logger.info("Bill #%s marked as paid (%s) by %s", bill.id, payment_method, request.user.username)
    messages.success(request, f"Bill #{bill.id} marked as paid.")
    return redirect("print_receipt", pk=bill.id)


# ─── Print Receipt ────────────────────────────────────────────────────────────

@login_required
def print_receipt(request, pk):
    bill = get_object_or_404(
        Bill.objects.select_related("patient", "consultation", "clinic")
        .prefetch_related("items", "payments"),
        pk=pk,
    )
    return render(request, "billing/receipt.html", {"bill": bill})


# ─── Revenue Report ───────────────────────────────────────────────────────────

@login_required
def revenue_report(request):
    clinic = _get_clinic(request.user)
    today = timezone.localdate()

    start_str = request.GET.get("start", "")
    end_str = request.GET.get("end", "")

    if start_str and end_str:
        try:
            start_date = date.fromisoformat(start_str)
            end_date = date.fromisoformat(end_str)
        except ValueError:
            start_date = today.replace(day=1)
            end_date = today
    else:
        start_date = today.replace(day=1)
        end_date = today

    total_revenue = revenue_in_range(clinic=clinic, start=start_date, end=end_date)
    tithe = total_revenue * Decimal("0.10")

    q = request.GET.get("q", "").strip()
    payments_qs = (
        Payment.objects.filter(
            bill__clinic=clinic,
            status__in=["success", "manual"],
            paid_at__date__gte=start_date,
            paid_at__date__lte=end_date,
        )
        .select_related("bill__patient")
        .order_by("-paid_at")
    )
    if q:
        payments_qs = payments_qs.filter(bill__patient__name__icontains=q)

    # Revenue breakdown by payment method (always over the full date range, unaffected by name search)
    revenue_by_method = {}
    for entry in (
        Payment.objects.filter(
            bill__clinic=clinic,
            status__in=["success", "manual"],
            paid_at__date__gte=start_date,
            paid_at__date__lte=end_date,
        )
        .values("payment_method")
        .annotate(total=Sum("amount"))
        .order_by("-total")
    ):
        revenue_by_method[entry["payment_method"]] = entry["total"]

    paginator = Paginator(payments_qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "billing/revenue_report.html",
        {
            "page_obj": page_obj,
            "total_revenue": total_revenue,
            "tithe": tithe,
            "start_date": start_date,
            "end_date": end_date,
            "revenue_by_method": revenue_by_method,
            "query": q,
        },
    )


# ─── Initiate Payment (Paystack) ──────────────────────────────────────────────

@login_required
def initiate_payment(request, bill_id):
    bill = get_object_or_404(Bill, pk=bill_id)
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
    data = {
        "email": bill.patient.email,
        "amount": int(bill.net_amount * 100),
        "callback_url": request.build_absolute_uri("/billing/paystack/callback/"),
    }

    if bill.clinic.paystack_subaccount_id:
        data["subaccount"] = bill.clinic.paystack_subaccount_id

    try:
        response = http_requests.post(
            f"{PAYSTACK_BASE_URL}/transaction/initialize",
            headers=headers,
            json=data,
            timeout=15,
        )
        res_data = response.json()
    except http_requests.RequestException as exc:
        logger.error("Paystack init failed for bill #%s: %s", bill_id, exc, exc_info=True)
        messages.error(request, f"Payment gateway error: {exc}")
        return redirect("bill_detail", pk=bill_id)

    if res_data.get("status"):
        Payment.objects.create(
            bill=bill,
            reference=res_data["data"]["reference"],
            amount=bill.net_amount,
            status="pending",
        )
        logger.info("Paystack payment initiated for bill #%s, ref=%s", bill_id, res_data["data"]["reference"])
        return HttpResponseRedirect(res_data["data"]["authorization_url"])

    logger.warning("Paystack init returned failure for bill #%s: %s", bill_id, res_data.get("message"))
    messages.error(request, res_data.get("message", "Failed to initiate payment."))
    return redirect("bill_detail", pk=bill_id)


# ─── Paystack Webhook ─────────────────────────────────────────────────────────

@csrf_exempt
def paystack_webhook(request):
    reference_id = request.GET.get("trxref")
    txn = get_transaction_by_reference(reference_id)

    if txn and txn.get("status") == "success":
        try:
            payment = Payment.objects.get(reference=reference_id)
            payment.status = "success"
            payment.paid_at = timezone.now()
            payment.paystack_response = txn
            payment.save(update_fields=["status", "paid_at", "paystack_response"])
            payment.bill.is_paid = True
            payment.bill.save(update_fields=["is_paid"])
            logger.info("Paystack webhook: payment ref=%s confirmed, bill #%s marked paid", reference_id, payment.bill.id)
        except Payment.DoesNotExist:
            logger.warning("Paystack webhook: no Payment found for ref=%s", reference_id)
    else:
        logger.debug("Paystack webhook: ref=%s status not success (%s)", reference_id, txn.get("status") if txn else "no txn")

    return redirect("billing_dashboard")


# ─── Transactions ─────────────────────────────────────────────────────────────

@login_required
def transactions_view(request):
    try:
        clinic = _get_clinic(request.user)
        subaccount_code = clinic.paystack_subaccount_id if clinic else None
        raw_txns = get_last_n_subaccount_transactions(subaccount_code, n=20) if subaccount_code else []
    except Exception as exc:
        logger.error("transactions_view: failed to fetch Paystack transactions for %s: %s", request.user.username, exc, exc_info=True)
        raw_txns = []

    transactions = []
    for tx in raw_txns:
        customer = tx.get("customer") or {}
        transactions.append(
            {
                "reference": tx.get("reference", ""),
                "status": (tx.get("status") or "").capitalize(),
                "amount": tx.get("amount", 0) / 100,
                "currency": tx.get("currency", "KES"),
                "paid_at": tx.get("paid_at") or tx.get("paidAt"),
                "gateway": tx.get("gateway_response") or "-",
                "customer_name": (
                    f"{customer.get('first_name', '')} {customer.get('last_name', '')}".strip()
                    or customer.get("email", "-")
                ),
                "channel": tx.get("channel", "-"),
            }
        )

    return render(request, "billing/transactions.html", {"transactions": transactions})
