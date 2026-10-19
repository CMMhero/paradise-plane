# Kustomisasi Paradise Task Tracker: email pemberitahuan pesan

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0133_pesanlangsung'),
    ]

    operations = [
        migrations.AddField(
            model_name='pesanlangsung',
            name='dinotifikasi_pada',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
