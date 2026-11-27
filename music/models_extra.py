from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.db.models import Q


class UserMusicProfile(models.Model):
    """A user's declared and learned music-taste profile; not a psychological diagnosis."""
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="music_profile",
    )
    preferred_genres = models.ManyToManyField(
        "music.Genre", blank=True, related_name="preferred_by_profiles"
    )
    energy = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True,
                                 validators=[MinValueValidator(0), MaxValueValidator(1)])
    danceability = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True,
                                       validators=[MinValueValidator(0), MaxValueValidator(1)])
    valence = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True,
                                  validators=[MinValueValidator(0), MaxValueValidator(1)])
    acousticness = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True,
                                       validators=[MinValueValidator(0), MaxValueValidator(1)])
    instrumentalness = models.DecimalField(max_digits=4, decimal_places=3, null=True, blank=True,
                                           validators=[MinValueValidator(0), MaxValueValidator(1)])
    preferred_moods = models.JSONField(default=list, blank=True)
    preferred_activities = models.JSONField(default=list, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User music profile"
        verbose_name_plural = "User music profiles"

    def __str__(self):
        return f"Music taste - {self.user}"


class MusicInteraction(models.Model):
    class Event(models.TextChoices):
        VIEW = "view", "View"
        PLAY = "play", "Play"
        DOWNLOAD = "download", "Download"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                             null=True, blank=True, related_name="music_interactions")
    song = models.ForeignKey("music.Song", on_delete=models.CASCADE,
                             related_name="interactions")
    event = models.CharField(max_length=12, choices=Event.choices)
    session_key = models.CharField(max_length=64, blank=True)
    listened_seconds = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["song", "event", "created_at"], name="music_event_song_idx"),
            models.Index(fields=["user", "created_at"], name="music_event_user_idx"),
        ]

    def __str__(self):
        return f"{self.event}: {self.song}"


class FavoriteSong(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="favorite_music")
    song = models.ForeignKey("music.Song", on_delete=models.CASCADE,
                             related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "song"], name="unique_user_favorite_song")
        ]

    def __str__(self):
        return f"{self.user} ♥ {self.song}"


class Playlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             related_name="music_playlists")
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=300, blank=True)
    is_public = models.BooleanField(default=False)
    songs = models.ManyToManyField("music.Song", through="music.PlaylistSong",
                                   related_name="playlists", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        constraints = [
            models.UniqueConstraint(fields=["user", "name"], name="unique_playlist_name_per_user")
        ]

    def __str__(self):
        return self.name


class PlaylistSong(models.Model):
    playlist = models.ForeignKey(Playlist, on_delete=models.CASCADE, related_name="entries")
    song = models.ForeignKey("music.Song", on_delete=models.CASCADE, related_name="playlist_entries")
    position = models.PositiveIntegerField(default=0)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position", "added_at"]
        constraints = [
            models.UniqueConstraint(fields=["playlist", "song"], name="unique_song_in_playlist")
        ]
