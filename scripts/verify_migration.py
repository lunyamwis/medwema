#!/usr/bin/env python
"""
Verification script for the migrate_data management command.

Run after the migration to confirm that all new schema fields have been
populated correctly:

    python scripts/verify_migration.py

The script exits with code 0 if everything looks clean, or code 1 if any
issues are found so it can be used in CI / deployment pipelines.
"""

import os
import sys

# ---------------------------------------------------------------------------
# Bootstrap Django
# ---------------------------------------------------------------------------

# Place the project root (one level above this script) on sys.path so that
# Django can locate the 'setup' settings package.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _PROJECT_ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "setup.settings")

import django  # noqa: E402  -- must come after sys.path manipulation
django.setup()

# ---------------------------------------------------------------------------
# Imports (after django.setup())
# ---------------------------------------------------------------------------

from django.db.models import Q  # noqa: E402

from billing.models import Payment  # noqa: E402
from clinicmanager.models import Clinic  # noqa: E402
from emr.models import Lab, LabQueue  # noqa: E402
from patient.models import Consultation, Patient, Queue  # noqa: E402

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PASS = "\033[92m[PASS]\033[0m"
FAIL = "\033[91m[FAIL]\033[0m"
WARN = "\033[93m[WARN]\033[0m"
SEP  = "-" * 60


def check(label: str, count: int, *, warn_only: bool = False) -> bool:
    """Print a check result.  Returns True when the check is clean (count == 0)."""
    if count == 0:
        print(f"  {PASS}  {label}")
        return True
    tag = WARN if warn_only else FAIL
    print(f"  {tag}  {label}: {count} record(s) affected")
    return warn_only  # warn_only checks don't count as failures


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_patients() -> list:
    print("\nPatient")
    print(SEP)
    results = []

    no_number = Patient.objects.filter(
        Q(patient_number__isnull=True) | Q(patient_number="")
    ).count()
    results.append(check("patient_number populated", no_number))

    inactive = Patient.objects.filter(
        Q(is_active=False) | Q(is_active__isnull=True)
    ).count()
    results.append(check("is_active = True for all patients", inactive))

    return results


def check_consultations() -> list:
    print("\nConsultation")
    print(SEP)
    results = []

    no_number = Consultation.objects.filter(
        Q(consultation_number__isnull=True) | Q(consultation_number="")
    ).count()
    results.append(check("consultation_number populated", no_number))

    no_status = Consultation.objects.filter(
        Q(status__isnull=True) | Q(status="")
    ).count()
    results.append(check("status populated", no_status))

    return results


def check_payments() -> list:
    print("\nPayment")
    print(SEP)
    results = []

    no_receipt = Payment.objects.filter(
        Q(receipt_number__isnull=True) | Q(receipt_number="")
    ).count()
    results.append(check("receipt_number populated", no_receipt))

    return results


def check_clinics() -> list:
    print("\nClinic")
    print(SEP)
    results = []

    inactive = Clinic.objects.filter(
        Q(is_active=False) | Q(is_active__isnull=True)
    ).count()
    results.append(check("is_active = True for all clinics", inactive))

    return results


def check_queues() -> list:
    print("\nQueue")
    print(SEP)
    results = []

    no_priority = Queue.objects.filter(
        Q(priority__isnull=True) | Q(priority="")
    ).count()
    results.append(check("priority populated", no_priority))

    return results


def check_labs() -> list:
    print("\nLab")
    print(SEP)
    results = []

    no_clinic = Lab.objects.filter(clinic__isnull=True).count()
    results.append(check("clinic assigned to all labs", no_clinic, warn_only=True))

    return results


def check_lab_queues() -> list:
    print("\nLabQueue")
    print(SEP)
    results = []

    no_clinic = LabQueue.objects.filter(clinic__isnull=True).count()
    results.append(check("clinic assigned to all lab queue entries", no_clinic, warn_only=True))

    return results


# ---------------------------------------------------------------------------
# Summary counts
# ---------------------------------------------------------------------------

def print_summary() -> None:
    print("\nRecord counts")
    print(SEP)
    print(f"  Patients       : {Patient.objects.count():>8,}")
    print(f"  Consultations  : {Consultation.objects.count():>8,}")
    print(f"  Payments       : {Payment.objects.count():>8,}")
    print(f"  Clinics        : {Clinic.objects.count():>8,}")
    print(f"  Queues         : {Queue.objects.count():>8,}")
    print(f"  Labs           : {Lab.objects.count():>8,}")
    print(f"  Lab Queues     : {LabQueue.objects.count():>8,}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    print("=" * 60)
    print("  Medwema data-migration verification report")
    print("=" * 60)

    all_results = []
    all_results.extend(check_patients())
    all_results.extend(check_consultations())
    all_results.extend(check_payments())
    all_results.extend(check_clinics())
    all_results.extend(check_queues())
    all_results.extend(check_labs())
    all_results.extend(check_lab_queues())

    print_summary()

    failed = all_results.count(False)
    total  = len(all_results)

    print("\n" + "=" * 60)
    if failed == 0:
        print(f"  {PASS}  All {total} checks passed -- migration looks clean.")
        return 0
    else:
        print(f"  {FAIL}  {failed}/{total} check(s) failed -- review output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())