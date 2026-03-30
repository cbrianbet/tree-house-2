from django.core.management.base import BaseCommand
from property.models import Unit
from property.utils import notify_saved_search_matches


class Command(BaseCommand):
    help = 'Match all currently public units against saved searches and send notifications'

    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=1,
            help='Only consider units published within the last N days (default: 1)',
        )

    def handle(self, *args, **options):
        from django.utils import timezone
        from datetime import timedelta

        since = timezone.now() - timedelta(days=options['days'])
        units = Unit.objects.filter(
            is_public=True,
            is_occupied=False,
            updated_at__gte=since,
        ).select_related('property')

        matched = 0
        for unit in units:
            notify_saved_search_matches(unit)
            matched += 1

        self.stdout.write(self.style.SUCCESS(f'Processed {matched} unit(s) against saved searches.'))
