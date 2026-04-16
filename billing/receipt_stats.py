"""Aggregations for GET /api/billing/receipts/stats/."""
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from django.db.models import Count, Sum, Avg, DateTimeField
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import Payment, Receipt


def _quantize_money(value):
    d = Decimal(value or 0)
    return str(d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def _quantize_pct(value):
    d = Decimal(value or 0)
    return float(d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))


def build_receipt_stats_payload(filtered_receipts_qs):
    """
    `filtered_receipts_qs` is a Receipt queryset after role scope + optional property/month filters.
    `this_month_*` uses the active timezone’s current calendar month on Coalesce(paid_at, issued_at).
    """
    method_keys = [c[0] for c in Payment.PAYMENT_METHOD_CHOICES]
    zero_breakdown = {k: 0.0 for k in method_keys}

    total_count = filtered_receipts_qs.count()
    if total_count == 0:
        return {
            'total_count': 0,
            'this_month_count': 0,
            'this_month_total': '0.00',
            'method_breakdown': zero_breakdown.copy(),
            'average_amount': '0.00',
        }

    agg = filtered_receipts_qs.aggregate(
        sum_amt=Sum('payment__amount'),
        avg_amt=Avg('payment__amount'),
    )
    average_amount = _quantize_money(agg['avg_amt'])

    method_rows = filtered_receipts_qs.values('payment__payment_method').annotate(c=Count('id'))
    breakdown = {k: Decimal('0') for k in method_keys}
    for row in method_rows:
        m = row['payment__payment_method']
        if m in breakdown:
            breakdown[m] = Decimal(row['c']) * Decimal('100') / Decimal(total_count)
    method_breakdown = {k: _quantize_pct(breakdown[k]) for k in method_keys}

    now = timezone.now()
    y, mo = now.year, now.month
    start = timezone.make_aware(datetime(y, mo, 1))
    if mo == 12:
        end = timezone.make_aware(datetime(y + 1, 1, 1))
    else:
        end = timezone.make_aware(datetime(y, mo + 1, 1))

    this_month_qs = Receipt.objects.filter(
        pk__in=filtered_receipts_qs.values('pk'),
    ).annotate(
        _eff=Coalesce('payment__paid_at', 'issued_at', output_field=DateTimeField()),
    ).filter(_eff__gte=start, _eff__lt=end)

    this_month_count = this_month_qs.count()
    tm_agg = this_month_qs.aggregate(s=Sum('payment__amount'))
    this_month_total = _quantize_money(tm_agg['s'])

    return {
        'total_count': total_count,
        'this_month_count': this_month_count,
        'this_month_total': this_month_total,
        'method_breakdown': method_breakdown,
        'average_amount': average_amount,
    }
