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


def add_lab_result(request):
    consultations = Consultation.objects.all()
    lab_tests = LabTest.objects.filter(lab__lab_type="Internal")
    LabResultFormSet = modelformset_factory(LabResult, form=LabResultForm, extra=1, can_delete=True)
    if request.method == 'POST':
        formset = LabResultFormSet(request.POST)
        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.performed_by = request.user
                instance.save()

            messages.success(request, "Lab results added successfully.")
            return redirect('lab_dashboard')
    else:
        formset = LabResultFormSet(queryset=LabResult.objects.none())

    return render(request, 'emr/add_result.html', {'formset': formset, 'consultations': consultations, 'lab_tests': lab_tests})



def edit_lab_results(request, consultation_id):
    consultation = get_object_or_404(Consultation, id=consultation_id)
    lab_tests = LabTest.objects.filter(lab__lab_type="Internal")

    LabResultFormSet = modelformset_factory(
        LabResult,
        form=LabResultForm,
        extra=1,  # allow adding new results
        can_delete=True,
    )

    queryset = LabResult.objects.filter(consultation=consultation)

    if request.method == 'POST':
        formset = LabResultFormSet(request.POST, queryset=queryset)

        # remove 'id' from changed_data manually if formset fails
        for form in formset.forms:
            # import pdb; pdb.set_trace()
            # if not form.changed_data.get('id', None):
            form.fields['id'] = forms.IntegerField(required=False)

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
    lab_queue = LabQueue.objects.filter(status__in=["waiting", "in_progress"]).order_by("created_at")

    # Existing results logic...
    results_qs = (
        LabResult.objects.values("consultation__patient__name", "consultation_id")
        .annotate(total_tests=Count("id"), last_test=Max("result_date"))
    )

    if search_query:
        results_qs = results_qs.filter(consultation__patient__name__icontains=search_query)

    paginator = Paginator(results_qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(request, "emr/dashboard.html", {
        "page_obj": page_obj,
        "search_query": search_query,
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
    return redirect('lab_queue', lab_id=lab.id)




def send_to_lab(request, consultation_id):
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

        messages.success(request, f"✅ {patient.name} has been sent to the lab for selected tests.")
        return redirect('doctor_detail', pk=consultation.doctor.id)

    # Fallback for GET requests
    messages.error(request, "Invalid request method.")
    return redirect('doctor_detail', pk=consultation.doctor.id)



def lab_queue_count_api(request):
    count = LabQueue.objects.filter(status='in_progress').count()
    print(f"Lab queue count requested, current count: {count}")
    return JsonResponse({'count': count})
