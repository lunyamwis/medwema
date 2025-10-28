# patient/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from .models import Doctor, Patient, Consultation
from .forms import PatientForm, ConsultationForm
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML



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
    doctor = Doctor.objects.get(pk=pk)
    patients = doctor.patients.all()  # from related_name="patients"
    return render(request, "patient/doctor_detail.html", {"doctor": doctor, "patients": patients})


# List all doctors
def doctor_list(request):
    doctors = Doctor.objects.all()
    return render(request, 'patient/doctor_list.html', {'doctors': doctors})




# Show doctor details and assigned patients
def doctor_detail(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk)
    return render(request, 'patient/doctor_detail.html', {'doctor': doctor})



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

