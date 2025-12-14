import json
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.db.models import Sum
from django.views.decorators.csrf import csrf_exempt
from django.contrib import messages
from django.urls import reverse
from django.shortcuts import redirect
import requests
from django.utils.timezone import now
from .utils import get_last_n_subaccount_transactions, get_transaction_by_reference
from .models import Bill, Payment

PAYSTACK_SECRET_KEY = settings.PAYSTACK_SECRET_KEY
PAYSTACK_BASE_URL = "https://api.paystack.co"



def billing_dashboard(request):
    today = now().date()
    bills = Bill.objects.filter()
    last_3_bills = Bill.objects.filter(is_paid=True).order_by('-created_at')[:3]

    # Calculate total revenue for these last 3 bills
    total_revenue_last_3 = last_3_bills.aggregate(total=Sum("total_amount"))["total"] or 0

    return render(
        request,
        "billing/dashboard.html",
        {"bills": bills},
    )


def billing_list(request):
    bills = Bill.objects.select_related("patient", "consultation").order_by("-created_at")
    unpaid_bills = bills.filter(is_paid=False)
    return render(request, "billing/billing_list.html", {"bills": bills, "unpaid_bills": unpaid_bills})


def bill_detail(request, pk):
    bill = get_object_or_404(Bill, pk=pk)
    return render(request, "billing/bill_detail.html", {"bill": bill})

def print_receipt(request, pk):
    bill = get_object_or_404(Bill, pk=pk)
    return render(request, "billing/receipt.html", {"bill": bill})

def mark_bill_paid(request, pk):
    bill = get_object_or_404(Bill, pk=pk)

    # Record manual payment
    Payment.objects.create(
        bill=bill,
        amount=bill.total_amount,
        payment_method="CASH",
        paid_by=request.user,
    )

    bill.is_paid = True
    bill.save()

    messages.success(request, f"Bill #{bill.id} marked as paid.")
    # Redirect to print the receipt
    return redirect("print_receipt", pk=bill.id)


def revenue_report(request):
    start_date = request.GET.get("start")
    end_date = request.GET.get("end")
    payments = Payment.objects.filter(status__in=["success", "manual"])

    if start_date and end_date:
        payments = payments.filter(paid_at__range=[start_date, end_date])

    total_revenue = payments.aggregate(Sum("amount"))["amount__sum"] or Decimal("0.00")
    return render(request, "billing/revenue_report.html", {
        "payments": payments,
        "total_revenue": total_revenue,
        "start_date": start_date,
        "end_date": end_date,
    })


def initiate_payment(request, bill_id):
    bill = get_object_or_404(Bill, pk=bill_id)
    headers = {"Authorization": f"Bearer {PAYSTACK_SECRET_KEY}"}
    data = {
        "email": bill.patient.email,
        "amount": int(bill.total_amount * 100),
        "callback_url": request.build_absolute_uri("/billing/paystack/callback/"),
    }

    if bill.clinic.paystack_subaccount_id:
        data["subaccount"] = bill.clinic.paystack_subaccount_id

    response = requests.post(f"{PAYSTACK_BASE_URL}/transaction/initialize", headers=headers, json=data)
    res_data = response.json()
    if res_data["status"]:
        Payment.objects.create(
            bill=bill,
            reference=res_data["data"]["reference"],
            amount=bill.total_amount,
            status="pending"
        )
        return HttpResponseRedirect(res_data["data"]["authorization_url"])
    return JsonResponse(res_data)
    

@csrf_exempt
def paystack_webhook(request):
    # import pdb; pdb.set_trace()
    reference_id = request.GET.get("trxref")
    txn = get_transaction_by_reference(reference_id)

    if txn and txn['status'] == 'success':
        try:
            payment = Payment.objects.get(reference=reference_id)
            payment.status = "success"
            payment.paid_at = timezone.now()
            payment.save()
            payment.bill.is_paid = True
            payment.bill.save()
        except Payment.DoesNotExist:
            pass
    return redirect("billing_dashboard")



def transactions_view(request):
    clinic_subaccount_code = request.user.clinics.last().paystack_subaccount_id  # replace with your clinic object if dynamic
    transactions = get_last_n_subaccount_transactions(clinic_subaccount_code, n=6)

    # Format transactions for the template
    formatted_txns = []
    for tx in transactions:
        formatted_txns.append({
            "reference": tx["reference"],
            "status": tx["status"].capitalize(),
            "amount": tx["amount"] / 100,  # Paystack amounts are in the smallest currency unit
            "currency": tx["currency"],
            "paid_at": tx.get("paid_at") or tx.get("paidAt"),
            "gateway": tx.get("gateway_response") or "-",
            "customer_name": f"{tx['customer']['first_name']} {tx['customer']['last_name']}" if tx.get("customer") else "-",
            "channel": tx.get("channel"),
        })

    return render(request, "billing/transactions.html", {"transactions": formatted_txns})
