from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from foro.models import Community


class Command(BaseCommand):
    help = (
        'Create default communities (general, dueno-animales-agricultores, especialistas, agronegocios) and assign users accordingly'
    )

    def handle(self, *args, **options):
        User = get_user_model()
        # If an older 'empresarios' community exists, migrate/rename it to 'agronegocios'
        try:
            old = Community.objects.filter(slug='empresarios').first()
            if old:
                target = Community.objects.filter(slug='agronegocios').first()
                if target:
                    # move members from old to target and delete old
                    target.members.add(*old.members.all())
                    target.members_count = target.members.count()
                    target.save(update_fields=['members_count'])
                    old.delete()
                else:
                    # rename
                    old.slug = 'agronegocios'
                    old.name = 'Agronegocios'
                    old.save(update_fields=['slug', 'name'])
        except Exception:
            pass
            
        # Updated community structure to match exact requirements
        slugs = [
            ('general', 'General'),
            ('dueno-animales-agricultores', 'Dueños de Animales y Agricultores'),
            ('especialistas', 'Especialistas'),
            ('agronegocios', 'Agronegocios'),
        ]

        created = []
        for slug, name in slugs:
            comm, c = Community.objects.get_or_create(
                slug=slug,
                defaults={
                    'name': name,
                    'short_description': f'Comunidad {name}',
                    'created_by': None,
                    'cover_image': f'https://via.placeholder.com/1200x300.png?text={name.replace(" ", "+")}',
                    'avatar': f'https://via.placeholder.com/128.png?text={name[:1].upper()}',
                },
            )
            if c:
                created.append(comm.slug)

        self.stdout.write(self.style.SUCCESS('Ensured communities exist: %s' % ', '.join([s[0] for s in slugs])))

        # add all users to general
        general = Community.objects.get(slug='general')
        users = User.objects.all()
        general.members.add(*users)
        general.members_count = general.members.count()
        general.save(update_fields=['members_count'])
        self.stdout.write(self.style.SUCCESS('Added %d users to general community' % users.count()))

        # Updated role-based assignment to match exact requirements
        for user in users:
            role = getattr(user, 'role', None)
            if not role:
                continue
            # normalize role string to lowercase for common matches
            r = str(role).lower()
            if r in ('consumer', 'consumidor', 'consumidores'):
                # Consumer goes to dueños de animales y agricultores community
                c = Community.objects.get(slug='dueno-animales-agricultores')
                c.members.add(user)
                c.members_count = c.members.count()
                c.save(update_fields=['members_count'])
            elif r in ('veterinario', 'veterinarios', 'agronomo', 'agronomos', 'specialist', 'specialists', 'specialista', 'especialista', 'especialistas'):
                # Specialists (veterinarians and agronomists) go to especialistas community
                c = Community.objects.get(slug='especialistas')
                c.members.add(user)
                c.members_count = c.members.count()
                c.save(update_fields=['members_count'])
            elif r in ('businessman', 'empresario', 'empresarios'):
                # Businessmen go to agronegocios
                c = Community.objects.get(slug='agronegocios')
                c.members.add(user)
                c.members_count = c.members.count()
                c.save(update_fields=['members_count'])

        self.stdout.write(self.style.SUCCESS('Role-based assignment completed'))