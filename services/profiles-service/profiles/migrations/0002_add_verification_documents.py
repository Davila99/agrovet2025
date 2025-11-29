# Generated manually
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='specialistprofile',
            name='verification_title_id',
            field=models.IntegerField(blank=True, help_text='ID del media del título profesional', null=True),
        ),
        migrations.AddField(
            model_name='specialistprofile',
            name='verification_student_card_id',
            field=models.IntegerField(blank=True, help_text='ID del media del carnet de estudiante', null=True),
        ),
        migrations.AddField(
            model_name='specialistprofile',
            name='verification_graduation_letter_id',
            field=models.IntegerField(blank=True, help_text='ID del media de la carta de egresado', null=True),
        ),
    ]




