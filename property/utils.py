import math
from .models import SavedSearch


def notify_saved_search_matches(unit):
    """Find all matching saved searches and notify their owners when a unit is published."""
    from notifications.utils import create_notification

    prop = unit.property
    searches = SavedSearch.objects.filter(notify_on_match=True).select_related('user')

    for search in searches:
        if search.user == prop.owner:
            continue  # don't notify the property owner about their own listing

        f = search.filters

        if f.get('price_min') and unit.price is not None and unit.price < f['price_min']:
            continue
        if f.get('price_max') and unit.price is not None and unit.price > f['price_max']:
            continue
        if f.get('bedrooms') and unit.bedrooms < int(f['bedrooms']):
            continue
        if f.get('bathrooms') and unit.bathrooms < int(f['bathrooms']):
            continue
        if f.get('property_type') and prop.property_type != f['property_type']:
            continue
        if f.get('amenities') and f['amenities'].lower() not in (unit.amenities or '').lower():
            continue
        if f.get('parking') and not unit.parking_space:
            continue

        if f.get('lat') and f.get('lng') and f.get('radius_km') and prop.latitude and prop.longitude:
            lat = float(f['lat'])
            lng = float(f['lng'])
            radius_km = float(f['radius_km'])
            lat_diff = abs(prop.latitude - lat) * 111.0
            lng_diff = abs(prop.longitude - lng) * 111.0 * abs(math.cos(math.radians(lat)))
            distance_km = math.sqrt(lat_diff ** 2 + lng_diff ** 2)
            if distance_km > radius_km:
                continue

        create_notification(
            user=search.user,
            notification_type='new_listing',
            title=f'New match: {unit.name}',
            body=f'{unit.name} at {prop.name} matches your saved search "{search.name}".',
            action_url=f'/property/units/{unit.id}/',
        )
