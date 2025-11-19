from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from foro.models import Community


class Command(BaseCommand):
    help = (
        'Create default communities (general, consumidores, agroveterinarias, '
        'veterinarios, agronomos, especialistas) and assign users accordingly'
    )

    def handle(self, *args, **options):
        User = get_user_model()
        # If an older 'empresarios' community exists, migrate/rename it to 'agroveterinarias'
        try:
            old = Community.objects.filter(slug='empresarios').first()
            if old:
                target = Community.objects.filter(slug='agroveterinarias').first()
                if target:
                    # move members from old to target and delete old
                    target.members.add(*old.members.all())
                    target.members_count = target.members.count()
                    target.save(update_fields=['members_count'])
                    old.delete()
                else:
                    # rename
                    old.slug = 'agroveterinarias'
                    old.name = 'Agroveterinarias'
                    old.save(update_fields=['slug', 'name'])
        except Exception:
            pass
        slugs = [
            ('general', 'General'),
            ('consumidores', 'Consumidores'),
            ('agroveterinarias', 'Agroveterinarias'),
            ('veterinarios', 'Veterinarios'),
            ('agronomos', 'Agronomos'),
            ('especialistas', 'Especialistas'),
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

        # role-based assignment
        for user in users:
            role = getattr(user, 'role', None)
            if not role:
                continue
            # normalize role string to lowercase for common matches
            r = str(role).lower()
            if r in ('consumer', 'consumidor', 'consumidores'):
                c = Community.objects.get(slug='consumidores')
                c.members.add(user)
                c.members_count = c.members.count()
                c.save(update_fields=['members_count'])
            elif r in ('businessman', 'empresario', 'empresarios'):
                # map business role to agroveterinarias
                c = Community.objects.get(slug='agroveterinarias')
                c.members.add(user)
                c.members_count = c.members.count()
                c.save(update_fields=['members_count'])
            elif r in ('specialist', 'specialists', 'specialista', 'especialista', 'especialistas'):
                # Assign specialists to veterinarian/agronomist and especialistas
                for slug in ['veterinarios', 'agronomos', 'especialistas']:
                    c = Community.objects.get(slug=slug)
                    c.members.add(user)
                    c.members_count = c.members.count()
                    c.save(update_fields=['members_count'])

        self.stdout.write(self.style.SUCCESS('Role-based assignment completed'))