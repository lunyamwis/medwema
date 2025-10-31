# Create your views here.
from django.shortcuts import render, redirect
from django.forms import modelformset_factory
from .models import LabResult
from .forms import LabResultForm
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from django.contrib import messages
from django.db.models import Count, Max
from patient.models import Patient
from django.core.paginator import Paginator
from django.db.models import Q


def add_lab_result(request):
    LabResultFormSet = modelformset_factory(LabResult, form=LabResultForm, extra=1, can_delete=True)
    if request.method == 'POST':
        formset = LabResultFormSet(request.POST)
        if formset.is_valid():
            instances = formset.save(commit=False)
            for instance in instances:
                instance.performed_by = request.user
                instance.save()
            return redirect('dashboard')
    else:
        formset = LabResultFormSet(queryset=LabResult.objects.none())

    return render(request, 'emr/add_result.html', {'formset': formset})

def edit_lab_results(request, consultation_id):
    LabResultFormSet = modelformset_factory(LabResult, form=LabResultForm, extra=0, can_delete=True)
    queryset = LabResult.objects.filter(consultation_id=consultation_id)

    if request.method == 'POST':
        formset = LabResultFormSet(request.POST, queryset=queryset)
        if formset.is_valid():
            formset.save()
            messages.success(request, "Lab results updated successfully.")
            return redirect('dashboard')
    else:
        formset = LabResultFormSet(queryset=queryset)

    return render(request, 'emr/edit_results.html', {'formset': formset})


def print_lab_results(request, consultation_id):
    results = LabResult.objects.filter(consultation_id=consultation_id).select_related('consultation', 'lab_test')
    consultation = results.first().consultation if results.exists() else None
    html_string = render_to_string('emr/results_pdf.html', {'results': results, 'consultation': consultation})

    pdf = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="lab_results_{consultation_id}.pdf"'
    return response


def lab_dashboard(request):
    search_query = request.GET.get('search', '').strip()

    results_summary = (
        LabResult.objects
        .values('consultation__patient__id', 'consultation__patient__name')
        .annotate(
            total_tests=Count('id'),
            last_test=Max('result_date'),
            consultation_id=Max('consultation__id'),  # ✅ capture at least one consultation ID
        )
        .order_by('-last_test')
    )

    if search_query:
        results_summary = results_summary.filter(
            Q(consultation__patient__name__icontains=search_query)
        )

    paginator = Paginator(results_summary, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
    }
    return render(request, 'emr/dashboard.html', context)


def view_lab_results(request, consultation_id):
    results = LabResult.objects.filter(consultation_id=consultation_id).select_related('consultation', 'lab_test')
    consultation = results.first().consultation if results.exists() else None
    return render(request, 'emr/view_results.html', {
        'results': results,
        'consultation': consultation
    })
