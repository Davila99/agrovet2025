# Generated manual migration to add fields that exist in models.py but were not in the initial migration
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('chat', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='chatroom',
            name='name',
            field=models.CharField(max_length=150, blank=True, default=''),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='chatroom',
            name='is_private',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='chatroom',
            name='last_activity',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
