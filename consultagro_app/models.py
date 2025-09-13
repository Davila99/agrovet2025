from django.db import models

# Create your models here.
# --------------------------
# 1. Usuarios
# --------------------------
class User(models.Model):
    ROLE_CHOICES = [
        ("veterinario", "Veterinario"),
        ("agronomo", "Agrónomo"),
        ("propietario", "Propietario"),
    ]

    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, unique=True)
    password_hash = models.TextField()
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    is_online = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.full_name} ({self.role})"


# --------------------------
# 2. Perfiles de veterinarios
# --------------------------
class VetProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    description = models.TextField(blank=True, null=True)
    years_experience = models.PositiveIntegerField(blank=True, null=True)
    profile_image = models.TextField(blank=True, null=True)


# --------------------------
# 3. Perfiles de agrónomos
# --------------------------
class AgronomoProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    description = models.TextField(blank=True, null=True)
    years_experience = models.PositiveIntegerField(blank=True, null=True)
    profile_image = models.TextField(blank=True, null=True)


# --------------------------
# 4. Perfiles de propietarios
# --------------------------
class PropietarioProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, primary_key=True)
    description = models.TextField(blank=True, null=True)
    profile_image = models.TextField(blank=True, null=True)


# --------------------------
# 5. Especialidades
# --------------------------
class Specialty(models.Model):
    TYPE_CHOICES = [
        ("veterinario", "Veterinario"),
        ("agronomo", "Agrónomo"),
    ]

    name = models.CharField(max_length=100)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)

    def __str__(self):
        return f"{self.name} ({self.type})"


# --------------------------
# 6. Especialidades de usuarios (ManyToMany)
# --------------------------
class UserSpecialty(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    specialty = models.ForeignKey(Specialty, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("user", "specialty")


# --------------------------
# 7. Imágenes de trabajos realizados
# --------------------------
class WorkImage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    image_url = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)


# --------------------------
# 8. Chats
# --------------------------
class Chat(models.Model):
    user1 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chats_user1")
    user2 = models.ForeignKey(User, on_delete=models.CASCADE, related_name="chats_user2")
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(blank=True, null=True)
    rating = models.PositiveSmallIntegerField(blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.rating and (self.rating < 1 or self.rating > 5):
            raise ValueError("Rating must be between 1 and 5")
        super().save(*args, **kwargs)


# --------------------------
# 9. Mensajes
# --------------------------
class Message(models.Model):
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE)
    sender = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField(blank=True, null=True)
    image_url = models.TextField(blank=True, null=True)
    video_url = models.TextField(blank=True, null=True)
    audio_url = models.TextField(blank=True, null=True)
    file_url = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


# --------------------------
# 10. Bloqueos
# --------------------------
class Block(models.Model):
    blocker = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blocker")
    blocked = models.ForeignKey(User, on_delete=models.CASCADE, related_name="blocked")

    class Meta:
        unique_together = ("blocker", "blocked")


# --------------------------
# 11. Llamadas
# --------------------------
class Call(models.Model):
    TYPE_CHOICES = [
        ("audio", "Audio"),
        ("video", "Video"),
    ]

    caller = models.ForeignKey(User, on_delete=models.CASCADE, related_name="calls_made")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="calls_received")
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    started_at = models.DateTimeField(blank=True, null=True)
    ended_at = models.DateTimeField(blank=True, null=True)


# --------------------------
# 12. Notificaciones
# --------------------------
class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField()
    seen = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


# --------------------------
# 13. Anuncios
# --------------------------
class Ad(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=150)
    description = models.TextField()
    location = models.TextField(blank=True, null=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=8, blank=True, null=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, blank=True, null=True)
    distance_range_km = models.PositiveIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


# --------------------------
# 14. Imágenes del anuncio
# --------------------------
class AdImage(models.Model):
    ad = models.ForeignKey(Ad, on_delete=models.CASCADE)
    image_url = models.TextField()