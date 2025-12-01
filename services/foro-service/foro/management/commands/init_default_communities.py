"""
Management command to initialize default communities.
Communities are based on user roles:
- General: All users
- Ganaderos, Agricultores y Dueños de Animales: Consumer role
- Especialistas en Salud Animal y Vegetal: Specialist role
- Agronegocios: Businessman role
"""
from django.core.management.base import BaseCommand
from foro.models import Community


class Command(BaseCommand):
    help = 'Initialize default communities'

    def handle(self, *args, **options):
        default_communities = [
            {
                'name': 'General',
                'slug': 'general',
                'short_description': 'Comunidad general para todos los usuarios',
                'description': 'Espacio de discusión abierto para todos los miembros de la plataforma. Comparte ideas, preguntas y experiencias.',
            },
            {
                'name': 'Ganaderos, Agricultores y Dueños de Animales',
                'slug': 'ganaderos-agricultores-animales',
                'short_description': 'Comunidad para ganaderos, agricultores y dueños de mascotas',
                'description': 'Comunidad para ganaderos, agricultores y propietarios de animales que buscan información, consejos y compartir experiencias sobre el cuidado y manejo de sus animales y cultivos.',
            },
            {
                'name': 'Especialistas en Salud Animal y Vegetal',
                'slug': 'especialistas-salud',
                'short_description': 'Veterinarios, agrónomos y especialistas',
                'description': 'Comunidad para veterinarios, agrónomos, zootecnistas y profesionales dedicados a la salud animal y vegetal. Comparte conocimientos, casos clínicos y avances en tu campo.',
            },
            {
                'name': 'Agronegocios',
                'slug': 'agronegocios',
                'short_description': 'Agroveterinarias y empresas del sector',
                'description': 'Comunidad para propietarios y representantes de agroveterinarias, empresas agropecuarias y negocios del sector. Discute tendencias, oportunidades y estrategias de negocio.',
            },
        ]

        created_count = 0
        updated_count = 0
        for comm_data in default_communities:
            community, created = Community.objects.update_or_create(
                slug=comm_data['slug'],
                defaults=comm_data
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'✅ Created community: {community.name}'))
            else:
                updated_count += 1
                self.stdout.write(self.style.WARNING(f'🔄 Updated community: {community.name}'))

        self.stdout.write(self.style.SUCCESS(f'✅ Created {created_count} communities, updated {updated_count}'))
