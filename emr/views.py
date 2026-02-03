# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.forms import modelformset_factory, inlineformset_factory
from .models import LabResult, LabQueue, Lab, LabTest
from .forms import LabResultForm
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string
from django.utils import timezone
from weasyprint import HTML
from django import forms    

from django.contrib import messages
from django.db.models import Count, Max
from patient.models import Patient, Consultation, Queue
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from billing.models import Bill, Payment
from django.utils.dateparse import parse_date


from django.views.decorators.http import require_GET


@require_GET
def ajax_consultation_search(request):
    q = request.GET.get('q', '').strip()
    results = []
    if q:
        qs = Consultation.objects.filter(
            Q(patient__name__icontains=q) | Q(id__icontains=q)  # tweak fields to search
        )[:20]
    else:
        qs = Consultation.objects.none()

    for obj in qs:
        results.append({'id': obj.pk, 'text': str(obj)})
    return JsonResponse(results, safe=False)


@require_GET
def ajax_labtest_search(request):
    q = request.GET.get('q', '').strip()
    results = []
    if q:
        qs = LabTest.objects.filter(name__icontains=q)[:20]
    else:
        qs = LabTest.objects.none()
    for obj in qs:
        results.append({'id': obj.pk, 'text': str(obj)})
    return JsonResponse(results, safe=False)


def add_lab_result(request, consultation_id):
    consultations = Consultation.objects.all()[0:3]

    consultation_id = consultation_id if consultation_id else request.POST.get("consultation_id")
    # import pdb;pdb.set_trace()
    consultation = None
    if Consultation.objects.filter(id=consultation_id).exists():
        consultation = Consultation.objects.get(id=consultation_id) if consultation_id else None
    else:
        consultation = get_object_or_404(Consultation, id=consultation_id)
    lab_tests = [x.lab_test for x in LabQueue.objects.filter(consultation=consultation)]

    LabResultFormSet = modelformset_factory(LabResult, form=LabResultForm, extra=len(lab_tests), can_delete=True)
    if request.method == 'POST':
        formset = LabResultFormSet(request.POST)
        if formset.is_valid():
            instances = formset.save(commit=False)
            consultation.lab_findings = str([f"{x.lab_test.name}=> {x.result_name}: {x.result_value}" for x in instances])
            consultation.save()
            for instance in instances:
                instance.consultation = consultation
                instance.performed_by = request.user
                instance.save()
                
                

            messages.success(request, "Lab results added successfully.")
            return redirect('lab_dashboard')
    else:
        formset = LabResultFormSet(queryset=LabResult.objects.none())

    return render(request, 'emr/add_result.html', {'formset': formset, 'consultations': consultations, 'lab_tests': lab_tests, 'consultation':consultation})



def consultation_search(request):
    q = request.GET.get("q", "")

    consultations = (
        Consultation.objects
        .select_related("patient")
        .filter(patient__name__icontains=q)
        .only("id", "date", "patient__name")[:20]
    )

    data = [
        {
            "id": c.id,
            "label": f"{c.patient.name} ({c.date})"
        }
        for c in consultations
    ]

    return JsonResponse(data, safe=False)


def edit_lab_results(request, consultation_id):
    consultation = get_object_or_404(Consultation, id=consultation_id)
    lab_tests = LabTest.objects.filter(lab__lab_type="Internal")

    LabResultFormSet = modelformset_factory(
        LabResult,
        form=LabResultForm,
        extra=0,  # allow adding new results
        can_delete=True,
    )

    queryset = LabResult.objects.filter(consultation=consultation)

    if request.method == 'POST':
        formset = LabResultFormSet(request.POST, queryset=queryset)

        print('keys--',request.POST.keys())
        # remove 'id' from changed_data manually if formset fails
        # for form in formset.forms:
            # import pdb; pdb.set_trace()
            # if not form.changed_data.get('id', None):
            # form.fields['id'] = forms.IntegerField(required=False)

        if formset.is_valid():
            instances = formset.save(commit=False)

            for instance in instances:
                if not instance.consultation_id:
                    instance.consultation = consultation
                instance.save()

            for obj in formset.deleted_objects:
                obj.delete()

            messages.success(request, f"Lab results for {consultation.patient.name} updated successfully.")
            return redirect('lab_dashboard')
        else:
            print(formset.errors)
            messages.error(request, "Please correct the errors below.")
    else:
        formset = LabResultFormSet(queryset=queryset)

    return render(
        request,
        'emr/edit_results.html',
        {
            'formset': formset,
            'consultation': consultation,
            'lab_tests': lab_tests,
        }
    )


def print_lab_results(request, consultation_id):
    results = LabResult.objects.filter(consultation_id=consultation_id).select_related('consultation', 'lab_test')
    consultation = results.first().consultation if results.exists() else None
    html_string = render_to_string('emr/results_pdf.html', {'results': results, 'consultation': consultation})

    pdf = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="lab_results_{consultation_id}.pdf"'
    return response


@login_required
def lab_dashboard(request):
    search_query = request.GET.get("search", "")
    lab_queue = lab_queue = (
        LabQueue.objects
        .filter(status__in=["waiting", "in_progress"])
        .order_by("patient_id", "-consultation__date")  # latest consultation first
        .distinct("patient_id")  # one row per patient
    )


    # Existing results logic...
    results_qs = (
        LabResult.objects.values("consultation__patient__name", "consultation_id")
        .annotate(total_tests=Count("id"), last_test=Max("result_date"))
    )

    if search_query:
        results_qs = results_qs.filter(consultation__patient__name__icontains=search_query)



    historical_results_qs = LabResult.objects.all()

    patient_query = request.GET.get('patient', '')
    lab_test_query = request.GET.get('lab_test', '')
    result_date_from_raw = request.GET.get("result_date_from", "").strip()
    result_date_to_raw   = request.GET.get("result_date_to", "").strip()
    result_date_raw      = request.GET.get("result_date", "").strip()  # optional exact

    result_date_from = parse_date(result_date_from_raw) if result_date_from_raw else None
    result_date_to   = parse_date(result_date_to_raw) if result_date_to_raw else None
    result_date      = parse_date(result_date_raw) if result_date_raw else None

    filters = Q()

    if patient_query:
        filters &= Q(consultation__patient__name__icontains=patient_query)

    if lab_test_query:
        filters &= Q(lab_test__name__icontains=lab_test_query)


    if patient_query and lab_test_query:
        filters &= Q(
            consultation__patient__name__icontains=patient_query,
            lab_test__name__icontains=lab_test_query
        )
    if result_date:
        filters &= Q(result_date=result_date)
    else:
        if result_date_from:
            filters &= Q(result_date__gte=result_date_from)
        if result_date_to:
            filters &= Q(result_date__lte=result_date_to)

    
    if filters:
        historical_results_qs = historical_results_qs.filter(filters)

    historical_results_qs = historical_results_qs.order_by("-result_date", "-id").distinct()

    paginator = Paginator(results_qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    historical_paginator = Paginator(historical_results_qs, 10)
    historical_page_obj = historical_paginator.get_page(request.GET.get("historical_page"))

    return render(request, "emr/dashboard.html", {
        "page_obj": page_obj,
        "historical_page_obj": historical_page_obj,
        "search_query": search_query,
        "patient": patient_query,
        "lab_test": lab_test_query,
        "lab_queue": lab_queue,
    })


def view_lab_results(request, consultation_id):
    results = LabResult.objects.all()
    consultation = results.first().consultation if results.exists() else None
    return render(request, 'emr/view_results.html', {
        'results': results,
        'consultation': consultation
    })



# patient/views.py


def lab_queue_view(request, lab_id):
    lab = get_object_or_404(Lab, id=lab_id)
    queue = LabQueue.objects.filter(lab=lab, status__in=["waiting", "in_progress","inlab"]).order_by("queue_number")

    return render(request, "emr/dashboard.html", {
        "lab": lab,
        "queue": queue,
    })


@login_required
def start_lab_test(request, queue_id):
    queue_item = get_object_or_404(LabQueue, id=queue_id)
    queue_item.start()
    if Lab.objects.filter(lab_type="Internal").exists():
        internal_lab = Lab.objects.get(lab_type="Internal")
        queue_item.lab = internal_lab
        queue_item.save()
    

    messages.success(request, f"Started test for {queue_item.patient.name}.")
    return redirect('add_result')


@login_required
def complete_lab_test(request, queue_id):
    queue_item = get_object_or_404(LabQueue, id=queue_id)
    lab = get_object_or_404(Lab, lab_type="Internal")
    queue_item.complete()
    doctor_queue = Queue.objects.filter(
        clinic=queue_item.clinic,
        doctor=queue_item.consultation.doctor,
        patient=queue_item.patient,
        status="inlab"
    ).first()
    if doctor_queue:
        doctor_queue.status = "fromLab"
        doctor_queue.save()
    messages.success(request, f"Completed test for {queue_item.patient.name}.")
    return redirect('lab_dashboard')




def send_to_lab(request, consultation_id):
    consultation = None
    if consultation_id == 0:
        patient = get_object_or_404(Patient, id=request.POST.get("patient_id"))
        consultations = Consultation.objects.filter(patient=patient)
        if consultations.exists():
            consultation = consultations.latest('date')
        else:
            consultation = Consultation.objects.create(patient=patient, doctor=patient.doctor, date=timezone.now(),chief_complaints="N/A")
    else:
        consultation = get_object_or_404(Consultation, id=consultation_id)
    
    patient = consultation.patient
    clinic = patient.clinic

    if request.method == "POST":
        selected_lab_tests = request.POST.getlist("lab_tests")  # get selected tests from <select multiple>

        if not selected_lab_tests:
            messages.warning(request, "Please select at least one lab test.")
            return redirect('doctor_detail', pk=consultation.doctor.id)

        # ✅ Check if there is any in-progress test for this patient
        has_in_progress = LabQueue.objects.filter(
            patient=patient,
            status="in_progress"  # assuming your LabQueue has a status field
        ).exists()

        if has_in_progress:
            messages.warning(
                request,
                f"{patient.name} already has a test in progress. Wait for it to complete before adding new ones."
            )
            return redirect('doctor_detail', pk=consultation.doctor.id)

        # Create one LabQueue per selected test
        for lab_test_id in selected_lab_tests:
            lab_test = get_object_or_404(LabTest, id=lab_test_id)
            
            try:
                bill = Bill.objects.filter(patient=patient,is_paid=False).latest('created_at')
                bill.total_amount += lab_test.price
                bill.is_paid = False
                bill.save()
                
            except Exception as e:
                messages.error(request, f"Error creating bill for {lab_test.name}: {str(e)}")
                
            LabQueue.objects.create(
                clinic=clinic,
                patient=patient,
                consultation=consultation,
                lab_test=lab_test,
                status="in_progress",
            )

        # Update Doctor Queue status
        Queue.objects.filter(
            clinic=clinic,
            doctor=consultation.doctor,
            patient=patient,
            status__in=["waiting", "in_progress"]
        ).update(status="inlab")

        messages.success(request, f"✅ {patient.name} has been sent to the lab for selected tests successfully, with billing generated.")
        return redirect('doctor_detail', pk=consultation.doctor.id)

    # Fallback for GET requests
    messages.error(request, "Invalid request method.")
    return redirect('doctor_detail', pk=consultation.doctor.id)



def lab_queue_count_api(request):
    count = LabQueue.objects.filter(status='in_progress').count()
    print(f"Lab queue count requested, current count: {count}")
    return JsonResponse({'count': count})
