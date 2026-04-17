"""
Role-safe queryset for "who can I start a conversation with?"

Permission matrix (queryset layer — only these users are ever returned):

| Viewer role    | Eligible recipients (always excludes self) |
|----------------|--------------------------------------------|
| Admin / staff  | All users (broader directory).             |
| Landlord       | Active tenants on non-deleted units of    |
|                | non-deleted properties they own; agents    |
|                | appointed on those properties.             |
| Agent          | Property owners, other agents on the same  |
|                | managed properties, active tenants on      |
|                | units under those properties.              |
| Tenant         | Owners and appointed agents for           |
|                | properties where the tenant has an active  |
|                | lease (non-deleted unit); moving company   |
|                | users the tenant has a booking with.       |
| Artisan        | Submitters and property owners for         |
|                | maintenance requests the artisan is        |
|                | assigned to or has placed a bid on.        |
| MovingCompany  | Customers who booked this company; for     |
|                | customers, the moving company user on      |
|                | their bookings.                            |
| Other / none   | Empty queryset.                            |

Optional `property` query param:
  Intersects the above with {owner + appointed agents + active tenants on that
  property's units}. Viewer must have access to that property (same rules as
  property APIs: owner, appointed agent, active tenant on the property, admin,
  or artisan with maintenance activity on that property). MovingCompany users
  cannot scope by property (400).

Search uses case-insensitive substring match on username, first_name,
last_name, email, phone, and "first last" concatenation. Leading-wildcard
LIKE cannot use B-tree indexes; consider pg_trgm or dedicated search if this
becomes hot.
"""
from django.db.models import Q, QuerySet

from authentication.models import CustomUser, Role
from maintenance.models import MaintenanceRequest
from moving.models import MovingBooking
from property.models import Lease, Property, PropertyAgent


def _is_admin(user) -> bool:
    return user.is_staff or (
        getattr(user, 'role', None) is not None and user.role.name == Role.ADMIN
    )


def _active_lease_filter():
    return Q(is_active=True) & Q(unit__deleted_at__isnull=True)


def messaging_participants_base_queryset(viewer: CustomUser) -> QuerySet:
    """
    Users the viewer may invite when composing a new conversation.
    Excludes `viewer` from the queryset.
    """
    base = CustomUser.objects.exclude(pk=viewer.pk).select_related('role')

    if _is_admin(viewer):
        return base

    if not getattr(viewer, 'role_id', None):
        return base.none()

    role_name = viewer.role.name

    if role_name == Role.LANDLORD:
        tenant_ids = (
            Lease.objects.filter(
                unit__property__owner=viewer,
                unit__property__deleted_at__isnull=True,
            )
            .filter(_active_lease_filter())
            .values('tenant_id')
        )
        agent_ids = PropertyAgent.objects.filter(
            property__owner=viewer,
            property__deleted_at__isnull=True,
        ).values('agent_id')
        return base.filter(Q(pk__in=tenant_ids) | Q(pk__in=agent_ids))

    if role_name == Role.AGENT:
        prop_ids = PropertyAgent.objects.filter(agent=viewer).values('property_id')
        tenant_ids = (
            Lease.objects.filter(
                unit__property_id__in=prop_ids,
                unit__property__deleted_at__isnull=True,
            )
            .filter(_active_lease_filter())
            .values('tenant_id')
        )
        owner_ids = Property.objects.filter(
            pk__in=prop_ids,
            deleted_at__isnull=True,
        ).values('owner_id')
        other_agent_ids = PropertyAgent.objects.filter(
            property_id__in=prop_ids,
        ).exclude(agent=viewer).values('agent_id')
        return base.filter(
            Q(pk__in=tenant_ids) | Q(pk__in=owner_ids) | Q(pk__in=other_agent_ids)
        )

    if role_name == Role.TENANT:
        prop_ids = (
            Lease.objects.filter(
                tenant=viewer,
                unit__property__deleted_at__isnull=True,
            )
            .filter(_active_lease_filter())
            .values('unit__property_id')
        )
        owner_ids = Property.objects.filter(
            pk__in=prop_ids,
            deleted_at__isnull=True,
        ).values('owner_id')
        agent_ids = PropertyAgent.objects.filter(property_id__in=prop_ids).values(
            'agent_id'
        )
        mover_user_ids = MovingBooking.objects.filter(customer=viewer).values(
            'company__user_id'
        )
        return base.filter(
            Q(pk__in=owner_ids) | Q(pk__in=agent_ids) | Q(pk__in=mover_user_ids)
        )

    if role_name == Role.ARTISAN:
        involved = MaintenanceRequest.objects.filter(
            Q(assigned_to=viewer) | Q(bids__artisan=viewer)
        ).distinct()
        submitter_ids = involved.values('submitted_by_id')
        owner_ids = involved.values('property__owner_id')
        return base.filter(Q(pk__in=submitter_ids) | Q(pk__in=owner_ids))

    if role_name == Role.MOVING_COMPANY:
        as_company = MovingBooking.objects.filter(company__user=viewer).values(
            'customer_id'
        )
        as_customer = MovingBooking.objects.filter(customer=viewer).values(
            'company__user_id'
        )
        return base.filter(Q(pk__in=as_company) | Q(pk__in=as_customer))

    return base.none()


def viewer_may_filter_by_property(viewer: CustomUser, prop: Property) -> bool:
    if prop.deleted_at is not None:
        return False
    if _is_admin(viewer):
        return True
    if not getattr(viewer, 'role_id', None):
        return False
    name = viewer.role.name
    if name == Role.LANDLORD and prop.owner_id == viewer.pk:
        return True
    if name == Role.AGENT:
        return PropertyAgent.objects.filter(property=prop, agent=viewer).exists()
    if name == Role.TENANT:
        return Lease.objects.filter(
            tenant=viewer,
            unit__property=prop,
        ).filter(_active_lease_filter()).exists()
    if name == Role.ARTISAN:
        return MaintenanceRequest.objects.filter(
            property=prop,
        ).filter(Q(assigned_to=viewer) | Q(bids__artisan=viewer)).exists()
    return False


def property_directory_user_id_list(prop: Property) -> list:
    """Primary keys for owner, appointed agents, and active tenants on `prop`."""
    if prop.deleted_at is not None:
        return []
    ids = {prop.owner_id}
    ids.update(
        PropertyAgent.objects.filter(property=prop).values_list('agent_id', flat=True)
    )
    ids.update(
        Lease.objects.filter(unit__property=prop)
        .filter(_active_lease_filter())
        .values_list('tenant_id', flat=True)
    )
    return [i for i in ids if i is not None]


def apply_search(qs: QuerySet, search: str) -> QuerySet:
    """Search name/email/phone; supports two-token first+last heuristic."""
    term = (search or '').strip()
    if not term:
        return qs
    parts = term.split()
    q = (
        Q(username__icontains=term)
        | Q(first_name__icontains=term)
        | Q(last_name__icontains=term)
        | Q(email__icontains=term)
        | Q(phone__icontains=term)
    )
    if len(parts) >= 2:
        q |= Q(first_name__icontains=parts[0]) & Q(last_name__icontains=parts[-1])
    return qs.filter(q)
