# patient/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from .models import Doctor, Patient, Consultation, Queue
from emr.models import LabTest  
from django.http import JsonResponse
from .forms import PatientForm, ConsultationForm, LabResultFormSet
from django.http import HttpResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from weasyprint import HTML

from django.views.decorators.csrf import csrf_exempt


def new_consultation(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)

    if request.method == 'POST':
        form = ConsultationForm(request.POST)
        formset = LabResultFormSet(request.POST, prefix='lab_results')

        if form.is_valid() and formset.is_valid():
            consultation = form.save(commit=False)
            consultation.patient = patient
            consultation.doctor = patient.doctor
            consultation.save()

            formset.instance = consultation
            formset.save()

            messages.success(request, 'Consultation and lab results saved successfully.')
            return redirect('patient_detail', pk=patient.id)
        else:
            messages.error(request, 'Please fix errors in the form.')
    else:
        form = ConsultationForm()
        formset = LabResultFormSet(prefix='lab_results')

    return render(request, 'patient/new_consultation.html', {
        'form': form,
        'formset': formset,
        'patient': patient
    })



def edit_consultation(request, patient_id, consultation_id):
    consultation = get_object_or_404(Consultation, id=consultation_id)
    patient = consultation.patient

    if request.method == 'POST':
        form = ConsultationForm(request.POST, instance=consultation)
        formset = LabResultFormSet(request.POST, instance=consultation, prefix='lab_results')

        if form.is_valid() and formset.is_valid():
            form.save()
            formset.save()
            messages.success(request, 'Consultation and lab results updated successfully.')
            return redirect('patient_detail', pk=patient.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = ConsultationForm(instance=consultation)
        formset = LabResultFormSet(instance=consultation, prefix='lab_results')

    return render(request, 'patient/edit_consultation.html', {
        'form': form,
        'formset': formset,
        'patient': patient,
        'consultation': consultation
    })


@csrf_exempt
def add_lab_test(request):
    """AJAX endpoint to add a new Lab Test."""
    if request.method == 'POST':
        name = request.POST.get('name')
        description = request.POST.get('description', '')
        if not name:
            return JsonResponse({'error': 'Name is required'}, status=400)

        lab_test = LabTest.objects.create(name=name, description=description)
        return JsonResponse({'id': lab_test.id, 'name': lab_test.name})
    return JsonResponse({'error': 'Invalid request'}, status=400)


def register_patient(request):
    if request.method == "POST":
        form = PatientForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.clinic = request.user.clinics.last()
            patient.save()
            return redirect("patient_success")
    else:
        form = PatientForm()
    return render(request, "patient/register_patient.html", {"form": form})


def patient_success(request):
    return render(request, "patient/patient_success.html")


def doctor_detail(request, pk):
    doctor = get_object_or_404(Doctor, id=pk)
    queue = Queue.objects.filter(doctor=doctor, status__in=["waiting", "in_progress"]).order_by("queue_number")

    query = request.GET.get("q")
    patients = doctor.patients.all()

    if query:
        patients = patients.filter(name__icontains=query)

    paginator = Paginator(patients, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "patient/doctor_detail.html", {
        "doctor": doctor,
        "queue": queue,
        "page_obj": page_obj,
        "query": query,
    })

# List all doctors
def doctor_list(request):
    doctors = Doctor.objects.all()
    return render(request, 'patient/doctor_list.html', {'doctors': doctors})






@login_required
def patient_list(request):
    query = request.GET.get('q')
    page_number = request.GET.get('page')

    # Filter by clinic and optional search term
    patients = Patient.objects.filter(clinic=request.user.clinics.last())
    if query:
        patients = patients.filter(name__icontains=query)

    # Paginate results — 10 per page
    paginator = Paginator(patients.order_by('-date_registered'), 10)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query,
    }
    return render(request, 'patient/patient_list.html', context)


def patient_detail(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    return render(request, 'patient/patient_detail.html', {'patient': patient})


def patient_edit(request, pk):
    patient = get_object_or_404(Patient, pk=pk)
    if request.method == 'POST':
        form = PatientForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, f'{patient.name} has been updated successfully!')
            return redirect('patient_detail', pk=patient.pk)
    else:
        form = PatientForm(instance=patient)

    return render(request, 'patient/patient_edit.html', {'form': form, 'patient': patient})


def patient_consultations(request, patient_id):
    """
    Show consultation history for a patient (list view).
    """
    patient = get_object_or_404(Patient, id=patient_id)
    consultations = patient.consultations.order_by("-date")  # latest first
    return render(request, "patient/patient_consultations.html", {
        "patient": patient,
        "consultations": consultations,
    })


def consultation_detail(request, consultation_id):
    """
    Show a single consultation (read-only view) and provide buttons
    to export PDF or edit.
    """
    consultation = get_object_or_404(Consultation, id=consultation_id)
    return render(request, "patient/consultation_detail.html", {
        "consultation": consultation
    })


def consultation_pdf(request, consultation_id):
    """
    Render a consultation to a PDF and return it as an HTTP response.
    Uses WeasyPrint to turn HTML into PDF.
    """
    consultation = get_object_or_404(Consultation, id=consultation_id)
    html_string = render_to_string("patient/consultation_pdf.html", {"consultation": consultation})
    html = HTML(string=html_string, base_url=request.build_absolute_uri("/"))
    pdf = html.write_pdf()

    filename = f"consultation_{consultation.patient.name.replace(' ', '_')}_{consultation.id}.pdf"
    response = HttpResponse(pdf, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response



def add_to_queue(request, doctor_id, patient_id):
    doctor = get_object_or_404(Doctor, id=doctor_id)
    patient = get_object_or_404(Patient, id=patient_id)

    # Prevent duplicates
    if Queue.objects.filter(doctor=doctor, patient=patient, status='waiting').exists():
        messages.warning(request, f"{patient.name} is already in Dr. {doctor.name}'s queue.")
    else:
        next_number = Queue.objects.filter(doctor=doctor).count() + 1
        Queue.objects.create(doctor=doctor, patient=patient, queue_number=next_number, clinic=patient.clinic)
        messages.success(request, f"{patient.name} added to Dr. {doctor.name}'s queue.")

    return redirect('patient_list')


def add_to_queue_select(request, patient_id):
    if request.method == "POST":
        doctor_id = request.POST.get("doctor_id")
        doctor = get_object_or_404(Doctor, id=doctor_id)
        patient = get_object_or_404(Patient, id=patient_id)
        patient.doctor = doctor
        patient.save()

        if Queue.objects.filter(doctor=doctor, patient=patient, status='waiting').exists():
            messages.warning(request, f"{patient.name} is already in Dr. {doctor.name}'s queue.")
        else:
            next_number = Queue.objects.filter(doctor=doctor).count() + 1
            Queue.objects.create(doctor=doctor, patient=patient, queue_number=next_number, clinic=patient.clinic)
            messages.success(request, f"{patient.name} added to Dr. {doctor.name}'s queue.")

    return redirect('patient_list')


def start_consultation(request, queue_id):
    queue_item = get_object_or_404(Queue, id=queue_id)
    queue_item.start()

    # Redirect to new consultation form for this patient
    return redirect('new_consultation', patient_id=queue_item.patient.id)


def complete_consultation(request, queue_id):
    queue_item = get_object_or_404(Queue, id=queue_id)
    queue_item.complete()
    return redirect('doctor_detail', pk=queue_item.doctor.id)