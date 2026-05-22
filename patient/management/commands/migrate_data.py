"""
Data migration management command.

Populates new schema fields with appropriate default values for existing
production records that pre-date those fields being added.

Run with:
    python manage.py migrate_data
"""

import datetime

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q


class Command(BaseCommand):
    help = "Populate new schema fields with appropriate default values for existing production data"

    # ------------------------------------------------------------------ #
    # Entry point                                                          #
    # ------------------------------------------------------------------ #

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE("Starting data migration..."))
        self.stdout.write("")

        try:
            with transaction.atomic():
                self._migrate_patients()
                self._migrate_consultations()
                self._migrate_payments()
                self._migrate_clinics()
                self._migrate_queues()
                self._migrate_labs()
                self._migrate_lab_queues()

            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS("Data migration completed successfully."))

        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"Migration failed: {exc}"))
            raise

    # ------------------------------------------------------------------ #
    # Patient                                                              #
    # ------------------------------------------------------------------ #

    def _migrate_patients(self):
        from patient.models import Patient

        self.stdout.write("  [patients] Migrating patient_number and is_active ...")

        # --- patient_number --------------------------------------------------
        # The model save() generates per-clinic numbers with P{clinic_id:03d}{seq:05d}.
        # For backfilling we use a date-based sequential pattern P{YYYYMMDD}{seq:04d}
        # so that legacy backfill entries are clearly distinguishable and cannot
        # collide with new records produced by the model save().
        patients_without_number = list(
            Patient.objects.filter(
                Q(patient_number__isnull=True) | Q(patient_number="")
            ).order_by("id")
        )

        if patients_without_number:
            base_date = datetime.date.today().strftime("%Y%m%d")
            for i, patient in enumerate(patients_without_number, start=1):
                patient.patient_number = f"P{base_date}{i:04d}"

            Patient.objects.bulk_update(
                patients_without_number, ["patient_number"], batch_size=500
            )
            self.stdout.write(
                f"    patient_number set for {len(patients_without_number)} patient(s)."
            )
        else:
            self.stdout.write("    patient_number: all patients already have a number -- skipped.")

        # --- is_active -------------------------------------------------------
        updated = Patient.objects.filter(is_active=False).update(is_active=True)
        updated += Patient.objects.filter(is_active__isnull=True).update(is_active=True)
        self.stdout.write(f"    is_active set to True for {updated} patient(s).")

    # ------------------------------------------------------------------ #
    # Consultation                                                         #
    # ------------------------------------------------------------------ #

    def _migrate_consultations(self):
        from patient.models import Consultation

        self.stdout.write("  [consultations] Migrating consultation_number and status ...")

        # --- consultation_number ---------------------------------------------
        consultations_without_number = list(
            Consultation.objects.filter(
                Q(consultation_number__isnull=True) | Q(consultation_number="")
            ).order_by("id")
        )

        if consultations_without_number:
            base_date = datetime.date.today().strftime("%Y%m%d")
            for i, consultation in enumerate(consultations_without_number, start=1):
                consultation.consultation_number = f"C{base_date}{i:04d}"

            Consultation.objects.bulk_update(
                consultations_without_number, ["consultation_number"], batch_size=500
            )
            self.stdout.write(
                f"    consultation_number set for {len(consultations_without_number)} consultation(s)."
            )
        else:
            self.stdout.write(
                "    consultation_number: all consultations already have a number -- skipped."
            )

        # --- status ----------------------------------------------------------
        # Records that pre-date the status field should be treated as completed.
        # Handle both NULL and empty-string cases from different migration paths.
        updated_null = Consultation.objects.filter(status__isnull=True).update(status="completed")
        updated_empty = Consultation.objects.filter(status="").update(status="completed")
        total_status = updated_null + updated_empty
        if total_status:
            self.stdout.write(f"    status set to 'completed' for {total_status} consultation(s).")
        else:
            self.stdout.write("    status: all consultations already have a status -- skipped.")

    # ------------------------------------------------------------------ #
    # Payment                                                              #
    # ------------------------------------------------------------------ #

    def _migrate_payments(self):
        from billing.models import Payment

        self.stdout.write("  [payments] Migrating receipt_number ...")

        payments_without_receipt = list(
            Payment.objects.filter(
                Q(receipt_number__isnull=True) | Q(receipt_number="")
            ).order_by("id")
        )

        if payments_without_receipt:
            today_str = datetime.date.today().strftime("%Y%m%d")
            for i, payment in enumerate(payments_without_receipt, start=1):
                if payment.paid_at:
                    date_str = payment.paid_at.strftime("%Y%m%d")
                else:
                    date_str = today_str
                payment.receipt_number = f"RCP{date_str}{i:04d}"

            Payment.objects.bulk_update(
                payments_without_receipt, ["receipt_number"], batch_size=500
            )
            self.stdout.write(
                f"    receipt_number set for {len(payments_without_receipt)} payment(s)."
            )
        else:
            self.stdout.write("    receipt_number: all payments already have a number -- skipped.")

    # ------------------------------------------------------------------ #
    # Clinic                                                               #
    # ------------------------------------------------------------------ #

    def _migrate_clinics(self):
        from clinicmanager.models import Clinic

        self.stdout.write("  [clinics] Migrating is_active ...")

        updated = Clinic.objects.filter(is_active=False).update(is_active=True)
        updated += Clinic.objects.filter(is_active__isnull=True).update(is_active=True)
        if updated:
            self.stdout.write(f"    is_active set to True for {updated} clinic(s).")
        else:
            self.stdout.write("    is_active: all clinics already active -- skipped.")

    # ------------------------------------------------------------------ #
    # Queue                                                                #
    # ------------------------------------------------------------------ #

    def _migrate_queues(self):
        from patient.models import Queue

        self.stdout.write("  [queues] Migrating priority ...")

        updated = Queue.objects.filter(
            Q(priority__isnull=True) | Q(priority="")
        ).update(priority="normal")

        if updated:
            self.stdout.write(f"    priority set to 'normal' for {updated} queue entry(ies).")
        else:
            self.stdout.write("    priority: all queue entries already have a priority -- skipped.")

    # ------------------------------------------------------------------ #
    # Lab                                                                  #
    # ------------------------------------------------------------------ #

    def _migrate_labs(self):
        from clinicmanager.models import Clinic
        from emr.models import Lab

        self.stdout.write("  [labs] Assigning clinic to labs that have none ...")

        labs_without_clinic = Lab.objects.filter(clinic__isnull=True)
        count = labs_without_clinic.count()

        if count == 0:
            self.stdout.write("    clinic: all labs already have a clinic -- skipped.")
            return

        default_clinic = Clinic.objects.filter(is_active=True).first()
        if not default_clinic:
            default_clinic = Clinic.objects.first()

        if not default_clinic:
            self.stdout.write(
                self.style.WARNING(
                    f"    WARNING: {count} lab(s) have no clinic but no Clinic record "
                    "exists in the database -- cannot assign. Skipping."
                )
            )
            return

        updated = labs_without_clinic.update(clinic=default_clinic)
        self.stdout.write(
            f"    clinic assigned to {updated} lab(s) "
            f"using '{default_clinic.name}' (id={default_clinic.pk})."
        )

    # ------------------------------------------------------------------ #
    # LabQueue                                                             #
    # ------------------------------------------------------------------ #

    def _migrate_lab_queues(self):
        from emr.models import LabQueue

        self.stdout.write("  [lab queues] Checking for lab queue entries without clinic ...")

        # LabQueue.clinic is a non-nullable FK in the current schema.
        # We guard against edge cases where the column was added without a
        # NOT NULL constraint during a zero-downtime deployment.
        lab_queues_without_clinic = LabQueue.objects.filter(
            clinic__isnull=True
        ).select_related("patient__clinic")

        count = lab_queues_without_clinic.count()
        if count == 0:
            self.stdout.write("    clinic: all lab queue entries already have a clinic -- skipped.")
            return

        assigned = 0
        skipped = 0
        for lq in lab_queues_without_clinic:
            if lq.patient and lq.patient.clinic_id:
                lq.clinic_id = lq.patient.clinic_id
                lq.save(update_fields=["clinic"])
                assigned += 1
            else:
                skipped += 1

        self.stdout.write(
            f"    clinic assigned to {assigned} lab queue entry(ies) from patient.clinic."
        )
        if skipped:
            self.stdout.write(
                self.style.WARNING(
                    f"    WARNING: {skipped} lab queue entry(ies) could not be assigned a clinic "
                    "(patient has no clinic) -- manual intervention required."
                )
            )