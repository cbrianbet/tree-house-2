from django.utils import timezone


def generate_receipt_number():
    from .models import Receipt
    now = timezone.now()
    prefix = f"RCP-{now.strftime('%Y%m')}-"
    last = Receipt.objects.filter(receipt_number__startswith=prefix).order_by('-receipt_number').first()
    seq = int(last.receipt_number.split('-')[-1]) + 1 if last else 1
    return f"{prefix}{seq:04d}"


def generate_invoice_number(pk):
    """Deterministic invoice number from primary key: INV-0035 for pk=35."""
    return f"INV-{pk:04d}"
