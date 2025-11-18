from django.db import models
from authentication.models import User



class Clinic(models.Model):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255, blank=True, null=True)
    phone_number = models.CharField(max_length=50, blank=True, null=True)
    created_by = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="clinic"
    )
    staff = models.ManyToManyField(
        User, related_name="clinics", blank=True, help_text="Clinic staff members"
    )
    date_created = models.DateTimeField(auto_now_add=True)
    paystack_subaccount_id = models.CharField(max_length=255, blank=True, null=True)


    def __str__(self):
        return self.name

class ClinicBankDetails(models.Model):
    CURRENCIES = [
        ("KES", "Kenyan Shilling"),
    ]
    ACCOUNT_TYPES = [
        ("bank", "Bank"),
        ("mobile_money", "Mobile Money"),
    ]
    BANKS = [
        (191, "Absa Bank Kenya Plc"),
        (208, "Access Bank Kenya"),
        (211, "African BankingCorporation"),
        (204, "Bank of Africa Kenya"),
        (193, "Bank of Baroda (K)"),
        (192, "Bank of India (K)"),
        (719, "Caritas Microfinance Bank"),
        (717, "Choice Microfinance Bank"),
        (201, "Citibank N.A."),
        (198, "Co-operative Bank of Kenya"),
        (291, "Commercial International Bank"),
        (206, "Consolidated Bank of Kenya"),
        (207, "Credit Bank"),
        (223, "Development Bank of Kenya"),
        (225, "Diamond Trust Bank Kenya"),
        (288, "Dubai Islamic Bank Kenya"),
        (215, "Ecobank Kenya"),
        (227, "Equity Bank Kenya"),
        (228, "Family Bank"),
        (292, "Faulu Microfinance Bank"),
        (219, "Guaranty Trust Bank Kenya"),
        (221, "Guardian Bank"),
        (229, "Gulf African Bank"),
        (195, "Habib Bank"),
        (289, "Housing Finance Cooperation Kenya (HFC Bank)"),
        (222, "I&M Bank"),
        (189, "Kenya Commercial Bank (Kenya)"),
        (290, "Kenya Women Microfinance Bank"),
        (721, "Kingdom Bank"),
        (200, "M-Oriental Bank"),
        (203, "Middle East Bank Kenya"),
        (199, "National Bank of Kenya"),
        (194, "NCBA Bank Kenya"),
        (809, "NCBA Loop"),
        (217, "Paramount Universal Bank"),
        (293, "PostBank Kenya"),
        (294, "Premier Bank Kenya"),
        (197, "Prime Bank"),
        (209, "SBM Bank Kenya"),
        (226, "Sidian Bank"),
        (216, "Spire Bank"),
        (210, "Stanbic Bank Kenya"),
        (190, "Standard Chartered Bank Kenya"),
        (723, "Stima Sacco"),
        (230, "UBA Kenya Bank"),
        (805, "UMBA Microfinance Bank"),
        (806, "Unaitas Sacco"),
        (220, "Victoria Commercial Bank"),
        (807, "Vooma"),
        (819, "Airtel Kenya"),
        (231, "M-PESA"),
        (798, "M-PESA Paybill"),
        (799, "M-PESA Till Number"),
        (808, "Telkom Kenya"),
    ]
    clinic = models.ForeignKey(
        Clinic, on_delete=models.CASCADE, related_name='bank_details'
    )
    bank_name = models.IntegerField(choices=BANKS)
    account_number = models.CharField(max_length=100)
    paybill_number = models.CharField(max_length=70, blank=True, null=True)
    till_number = models.CharField(max_length=70, blank=True, null=True)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default="bank")
    currency = models.CharField(max_length=10, choices=CURRENCIES, default="KES")   
    account_name = models.CharField(max_length=255)
    date_created = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.clinic.name} - {self.bank_name}"
        