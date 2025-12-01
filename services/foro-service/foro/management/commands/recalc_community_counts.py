from django.core.management.base import BaseCommand
from foro.models import Community


class Command(BaseCommand):
    help = 'Recalculate members_count for all communities from members_ids JSON field'

    def handle(self, *args, **options):
        qs = Community.objects.all()
        total = qs.count()
        self.stdout.write(f'Recalculating members_count for {total} communities...')
        for c in qs:
            try:
                # Debug: print raw members_ids before update
                raw = c.members_ids
                self.stdout.write(f'Community {c.id} slug={c.slug} raw members_ids type={type(raw)} repr={repr(raw)}')
                c.update_members_count()
                self.stdout.write(f'Updated community {c.id} -> members_count={c.members_count}')
            except Exception as e:
                self.stderr.write(f'Failed to update community {c.id}: {e}')
        self.stdout.write(self.style.SUCCESS('Recalculation completed.'))
