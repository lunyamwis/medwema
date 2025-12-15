# patient/views.py
import json
import os
from openai import OpenAI
from django.shortcuts import render, redirect, get_object_or_404
from django.db import transaction
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
from billing.models import Bill, Payment
from weasyprint import HTML

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

client = OpenAI()

@csrf_exempt
@require_http_methods(["POST"])
def speech_to_consultation(request, patient_id):
    """
    Endpoint to convert speech text to consultation notes using OpenAI.
    Expects JSON payload with 'transcript' field.
    """
    data = json.loads(request.body)
    transcript = data.get('transcript', '')

    if not transcript:
        return JsonResponse({'error': 'Transcript is required'}, status=400)

    with open('consultation_schema.json', 'r') as f:
        schema_above = json.load(f)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"Extract consultation data from speech transcript into JSON schema. Only return valid JSON matching this exact schema:{json.dumps(schema_above)}. Focus on medical details from speech."},
                {"role": "user", "content": f"Extract from: {transcript}"}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}  # Ensure the response is in JSON object format
        )

        consultation_data = json.loads(response.choices[0].message.content)
        print(f"Extracted consultation data: {consultation_data}")
        patient = get_object_or_404(Patient, id=patient_id)
        doctor = patient.doctor
        consultation = None
        try:
            consultation = Consultation.objects.create(**consultation_data.get('clinical_details', {}),
                **consultation_data.get('vitals', {}),
                **consultation_data.get('examinations', {}),
                **consultation_data.get('investigations', {}),
                **consultation_data.get('diagnosis_management', {}),
                patient=patient,
                doctor=doctor
            )
            print("Consultation created successfully.")
        except Exception as e:
            print("Error creating consultation:", e)
        
        return JsonResponse({
            'success': True,
            'consultation_id': consultation.id if consultation else None,
            'message': 'Consultation created from speech'
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)



def new_consultation(request, patient_id):
    patient = get_object_or_404(Patient, id=patient_id)
    if request.method == "POST":
        form = ConsultationForm(request.POST)
        if form.is_valid():
            consultation = form.save(commit=False)
            consultation.patient = patient
            consultation.doctor = patient.doctor
            consultation.save()
            return redirect('doctor_detail', pk=patient.doctor.id)
    else:
        form = ConsultationForm()

    return render(request, 'patient/new_consultation.html', {
        'form': form,
        'patient': patient
    })


def edit_consultation(request, patient_id, consultation_id):
    patient = get_object_or_404(Patient, id=patient_id)
    consultation = get_object_or_404(Consultation, id=consultation_id, patient=patient)

    if request.method == "POST":
        form = ConsultationForm(request.POST, instance=consultation)
        if form.is_valid():
            form.save()
            messages.success(request, "Consultation updated successfully.")
            return redirect('consultation_detail', consultation_id=consultation.id)
    else:
        form = ConsultationForm(instance=consultation)

    return render(request, 'patient/edit_consultation.html', {
        'form': form,
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


def consultation_list(request):
    consultations = Consultation.objects.select_related("patient", "doctor").order_by("-date")
    paginator = Paginator(consultations, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)
    return render(request, "patient/consultation_list.html", {"page_obj": page_obj})


def doctor_detail(request, pk):
    doctor = get_object_or_404(Doctor, id=pk)
    queue = Queue.objects.filter(doctor=doctor, status__in=["waiting", "in_progress", "fromLab"]).order_by("queue_number")
    lab_tests = LabTest.objects.filter(lab__lab_type="Internal")

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
        "lab_tests": lab_tests,
    })

# List all doctors
def doctor_list(request):
    doctors = Doctor.objects.all()
    return render(request, 'patient/doctor_list.html', {'doctors': doctors})




def patient_queue_count_api(request):
    count = Queue.objects.filter(status__in=['in_progress','waiting']).count()
    print(f"Patient queue count requested, current count: {count}")
    return JsonResponse({'count': count})

@login_required
def patient_list(request):
    query = request.GET.get('q')
    page_number = request.GET.get('page')

    # Filter by clinic and optional search term
    patients = Patient.objects.filter(clinic=request.user.clinics.last())
    if query:
        patients = patients.filter(name__icontains=query)

    completed = Queue.objects.filter(status__in=['completed']).count()
    # Paginate results — 10 per page
    paginator = Paginator(patients.order_by('-date_registered'), 10)
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'query': query,
        'completed': completed,
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
        return redirect('patient_list')

    # Determine the consultation fee based on previous bills
    previous_bills_count = Bill.objects.filter(patient=patient).count()
    if previous_bills_count == 0:
        consultation_fee = 1500  # first time
    else:
        consultation_fee = 1300  # second time or more

    # Wrap billing + queue addition in a transaction
    # with transaction.atomic():
    # Create a Bill, set consultation=None if not available yet
    Bill.objects.create(
        patient=patient,
        consultation=None,  # No consultation linked yet
        clinic=patient.clinic,
        total_amount=consultation_fee,
        is_paid=False
    )

    # Add patient to the queue
    next_number = Queue.objects.filter(doctor=doctor).count() + 1
    Queue.objects.create(
        doctor=doctor,
        patient=patient,
        queue_number=next_number,
        clinic=patient.clinic
    )

    messages.success(
        request,
        f"{patient.name} has been billed {consultation_fee} and added to Dr. {doctor.name}'s queue."
    )

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
    consultation = queue_item.patient.consultations.last()
    bill, created_bill = Bill.objects.get_or_create(
        consultation=consultation,
        defaults={'patient':consultation.patient, 'clinic': consultation.patient.clinic}
    )
    bill.total_amount += consultation.labor_charges or 0
    bill.is_paid = False
    bill.save()
    return redirect('doctor_detail', pk=queue_item.doctor.id)


def patient_complete_count_api(request):
    count = Queue.objects.filter(status__in=['completed']).count()
    print(f"Patient queue complete count requested, current count: {count}")
    return JsonResponse({'count': count})




def pipeline_notification(request):
    return render(request, 'patient/pipeline_notification.html')