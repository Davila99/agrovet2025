"""
Management command to initialize default communities.
"""
from django.core.management.base import BaseCommand
from foro.models import Community


class Command(BaseCommand):
    help = 'Initialize default communities'

    def handle(self, *args, **options):
        default_communities = [
            {
                'name': 'Consumidores',
                'slug': 'consumidores',
                'short_description': 'Comunidad para consumidores',
            },
            {
                'name': 'Agroveterinarias',
                'slug': 'agroveterinarias',
                'short_description': 'Comunidad para agroveterinarias',
            },
            {
                'name': 'Veterinarios',
                'slug': 'veterinarios',
                'short_description': 'Comunidad para veterinarios',
            },
            {
                'name': 'Agrónomos',
                'slug': 'agronomos',
                'short_description': 'Comunidad para agrónomos',
            },
            {
                'name': 'Especialistas',
                'slug': 'especialistas',
                'short_description': 'Comunidad para especialistas',
            },
        ]

        created_count = 0
        for comm_data in default_communities:
            community, created = Community.objects.get_or_create(
                slug=comm_data['slug'],
                defaults=comm_data
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✅ Created community: {community.name}'))

        self.stdout.write(self.style.SUCCESS(f'✅ Created {created_count} communities'))

