from datetime import datetime

from django.db.models import Q, Value, CharField, DateTimeField
from django.db.models.functions import Coalesce, Concat, Trim
from django.utils import timezone as dj_timezone


def validate_receipt_list_query_params(query_params, allowed_payment_methods):
    """
    Parse and validate receipt list query params.
    Returns (errors_dict, parsed_dict). If errors_dict is non-empty, return 400.
    """
    errors = {}
    parsed = {}

    prop = (query_params.get('property') or '').strip()
    if prop:
        try:
            pid = int(prop)
            if pid < 1:
                raise ValueError
            parsed['property_id'] = pid
        except ValueError:
            errors['property'] = ['property must be a positive integer.']

    method = (query_params.get('method') or '').strip()
    if method:
        m = method.lower()
        if m not in allowed_payment_methods:
            errors['method'] = [
                f'Invalid method. Must be one of: {", ".join(sorted(allowed_payment_methods))}.',
            ]
        else:
            parsed['method'] = m

    month = (query_params.get('month') or '').strip()
    if month:
        try:
            parts = month.split('-')
            if len(parts) != 2:
                raise ValueError
            y, mo = int(parts[0]), int(parts[1])
            datetime(y, mo, 1)
            if mo < 1 or mo > 12:
                raise ValueError
            parsed['month'] = (y, mo)
        except (ValueError, TypeError):
            errors['month'] = ['month must be YYYY-MM (e.g. 2026-04).']

    search = (query_params.get('search') or '').strip()
    if search:
        parsed['search'] = search

    return errors, parsed


def validate_receipt_stats_query_params(query_params):
    """Optional `property` and `month` (YYYY-MM) only; same validation rules as receipt list."""
    errors = {}
    parsed = {}

    prop = (query_params.get('property') or '').strip()
    if prop:
        try:
            pid = int(prop)
            if pid < 1:
                raise ValueError
            parsed['property_id'] = pid
        except ValueError:
            errors['property'] = ['property must be a positive integer.']

    month = (query_params.get('month') or '').strip()
    if month:
        try:
            parts = month.split('-')
            if len(parts) != 2:
                raise ValueError
            y, mo = int(parts[0]), int(parts[1])
            datetime(y, mo, 1)
            if mo < 1 or mo > 12:
                raise ValueError
            parsed['month'] = (y, mo)
        except (ValueError, TypeError):
            errors['month'] = ['month must be YYYY-MM (e.g. 2026-04).']

    return errors, parsed


def apply_receipt_list_filters(qs, parsed):
    """Apply validated filters to a scoped Receipt queryset (must use _receipt_base_queryset)."""
    if 'property_id' in parsed:
        qs = qs.filter(payment__invoice__lease__unit__property_id=parsed['property_id'])
    if 'method' in parsed:
        qs = qs.filter(payment__payment_method=parsed['method'])
    if 'month' in parsed:
        y, mo = parsed['month']
        start = dj_timezone.make_aware(datetime(y, mo, 1))
        if mo == 12:
            end = dj_timezone.make_aware(datetime(y + 1, 1, 1))
        else:
            end = dj_timezone.make_aware(datetime(y, mo + 1, 1))
        qs = qs.annotate(
            _receipt_month_anchor=Coalesce(
                'payment__paid_at',
                'issued_at',
                output_field=DateTimeField(),
            ),
        ).filter(_receipt_month_anchor__gte=start, _receipt_month_anchor__lt=end)
    if 'search' in parsed:
        term = parsed['search']
        qs = qs.annotate(
            _receipt_tenant_full=Trim(
                Concat(
                    Coalesce(
                        'payment__invoice__lease__tenant__first_name',
                        Value(''),
                        output_field=CharField(),
                    ),
                    Value(' '),
                    Coalesce(
                        'payment__invoice__lease__tenant__last_name',
                        Value(''),
                        output_field=CharField(),
                    ),
                    output_field=CharField(),
                ),
            ),
        ).filter(
            Q(receipt_number__icontains=term)
            | Q(payment__invoice__invoice_number__icontains=term)
            | Q(payment__invoice__lease__unit__name__icontains=term)
            | Q(payment__invoice__lease__tenant__email__icontains=term)
            | Q(payment__transaction_reference__icontains=term)
            | Q(_receipt_tenant_full__icontains=term)
        )
    return qs
