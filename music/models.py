
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import (
    FileExtensionValidator,
    MinValueValidator,
    MaxValueValidator,
)
from django.db import models
from django.utils.text import slugify
from .models_extra import (  # noqa: E402,F401
    UserMusicProfile,
    MusicInteraction,
    FavoriteSong,
    Playlist,
    PlaylistSong,
)

# =====================================================
# CONSTANTS
# =====================================================

AUDIO_EXTENSIONS = [
    "mp3",
    "wav",
    "ogg",
    "m4a",
    "aac",
]

IMAGE_EXTENSIONS = [
    "jpg",
    "jpeg",
    "png",
    "webp",
]

MAX_AUDIO_SIZE = 100 * 1024 * 1024  # 100 MB
MAX_IMAGE_SIZE = 5 * 1024 * 1024    # 5 MB


# =====================================================
# FILE VALIDATORS
# =====================================================

def validate_audio_size(value):
    """
    Check maximum allowed audio file size.
    """

    if value.size > MAX_AUDIO_SIZE:

        raise ValidationError(
            "Audio file size must not exceed 100 MB."
        )


def validate_image_size(value):
    """
    Check maximum allowed image file size.
    """

    if value.size > MAX_IMAGE_SIZE:

        raise ValidationError(
            "Image size must not exceed 5 MB."
        )


def validate_string_list(value):
    """
    Validate JSON fields that must contain
    a list of non-empty strings.
    """

    if not isinstance(value, list):

        raise ValidationError(
            "This field must contain a list."
        )

    if len(value) > 30:

        raise ValidationError(
            "Maximum number of tags is 30."
        )

    for item in value:

        if not isinstance(item, str) or not item.strip():

            raise ValidationError(
                "All items must be non-empty strings."
            )

        if len(item) > 60:

            raise ValidationError(
                "Each item must be at most 60 characters."
            )


# =====================================================
# ARTIST MODEL
# =====================================================

class Artist(models.Model):

    # Artist's name
    name = models.CharField(
        max_length=150,
        db_index=True,
    )

    # Short biography
    bio = models.TextField(
        blank=True
    )

    # Artist's profile photo
    photo = models.ImageField(
        upload_to="music/artists/",
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=IMAGE_EXTENSIONS
            ),
            validate_image_size,
        ]
    )

    # Creation date
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = ["name"]

        verbose_name = "Artist"
        verbose_name_plural = "Artists"

    def __str__(self):

        return self.name


# =====================================================
# GENRE MODEL
# =====================================================

class Genre(models.Model):

    # Genre name
    name = models.CharField(
        max_length=60,
        unique=True
    )

    # Short description of the genre
    description = models.CharField(
        max_length=250,
        blank=True
    )

    class Meta:

        ordering = ["name"]

        verbose_name = "Genre"
        verbose_name_plural = "Genres"

    def __str__(self):

        return self.name


# =====================================================
# ALBUM MODEL
# =====================================================

class Album(models.Model):

    # Album title
    title = models.CharField(
        max_length=200
    )

    # Album artists
    artists = models.ManyToManyField(
        Artist,
        related_name="albums",
        blank=True
    )

    # Album cover
    cover = models.ImageField(
        upload_to="music/albums/",
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=IMAGE_EXTENSIONS
            ),
            validate_image_size,
        ]
    )

    # Album release date
    release_date = models.DateField(
        blank=True,
        null=True
    )

    # Additional album information
    description = models.TextField(
        blank=True
    )

    # Creation date
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = ["-release_date", "title"]

        verbose_name = "Album"
        verbose_name_plural = "Albums"

    def __str__(self):

        return self.title


# =====================================================
# SONG MODEL
# =====================================================

class Song(models.Model):

    # -------------------------------------------------
    # 1. STATUS CHOICES
    # -------------------------------------------------

    class Status(models.TextChoices):

        DRAFT = "draft", "Draft"

        PUBLISHED = "published", "Published"

        ARCHIVED = "archived", "Archived"


    class RightsStatus(models.TextChoices):

        UNKNOWN = "unknown", "Unknown"

        PLATFORM_OWNED = "owned", "Platform Owned"

        LICENSED = "licensed", "Licensed"

        PUBLIC_DOMAIN = "public", "Public Domain"

        AUTHORIZED = "authorized", "Uploader Authorized"


    # -------------------------------------------------
    # 2. GENERAL INFORMATION
    # -------------------------------------------------

    title = models.CharField(
        max_length=200,
        db_index=True,
        help_text="The official title of the song."
    )

    slug = models.SlugField(
        max_length=220,
        unique=True,
        blank=True,
        help_text="A unique URL-friendly identifier."
    )

    artists = models.ManyToManyField(
        Artist,
        related_name="songs",
        help_text="Artists who performed this song."
    )

    album = models.ForeignKey(
        Album,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="songs"
    )

    genres = models.ManyToManyField(
        Genre,
        related_name="songs",
        blank=True
    )

    description = models.TextField(
        blank=True,
        help_text="Additional information about the song."
    )


    # -------------------------------------------------
    # 3. MEDIA FILES
    # -------------------------------------------------

    audio_file = models.FileField(
        upload_to="music/audio/%Y/%m/",
        max_length=255,
        validators=[
            FileExtensionValidator(
                allowed_extensions=AUDIO_EXTENSIONS
            ),
            validate_audio_size,
        ],
        help_text="Main audio file."
    )

    cover = models.ImageField(
        upload_to="music/covers/",
        blank=True,
        null=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=IMAGE_EXTENSIONS
            ),
            validate_image_size,
        ],
        help_text="Song cover image. Album cover can be used as fallback."
    )


    # -------------------------------------------------
    # 4. MUSIC METADATA
    # -------------------------------------------------

    duration_seconds = models.PositiveIntegerField(
        blank=True,
        null=True,
        validators=[
            MinValueValidator(1)
        ],
        help_text="Song duration in seconds."
    )

    release_date = models.DateField(
        blank=True,
        null=True
    )

    language_code = models.CharField(
        max_length=10,
        default="und",
        help_text="Language code, e.g. en, fa, es."
    )

    record_label = models.CharField(
        max_length=150,
        blank=True
    )

    track_number = models.PositiveSmallIntegerField(
        blank=True,
        null=True
    )

    is_explicit = models.BooleanField(
        default=False
    )


    # -------------------------------------------------
    # 5. DATA MINING / RECOMMENDATION FEATURES
    # -------------------------------------------------

    tempo_bpm = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(300)
        ],
        help_text="Song tempo in Beats Per Minute (BPM)."
    )

    energy = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        blank=True,
        null=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ]
    )

    danceability = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        blank=True,
        null=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ]
    )

    valence = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        blank=True,
        null=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ]
    )

    acousticness = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        blank=True,
        null=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ]
    )

    instrumentalness = models.DecimalField(
        max_digits=4,
        decimal_places=3,
        blank=True,
        null=True,
        validators=[
            MinValueValidator(0),
            MaxValueValidator(1)
        ]
    )

    # Emotional characteristics
    mood_tags = models.JSONField(
        default=list,
        blank=True,
        validators=[
            validate_string_list
        ]
    )

    # Suitable activities
    activity_tags = models.JSONField(
        default=list,
        blank=True,
        validators=[
            validate_string_list
        ]
    )


    # -------------------------------------------------
    # 6. LLM / SEMANTIC SEARCH FEATURES
    # -------------------------------------------------

    ai_summary = models.TextField(
        blank=True,
        help_text="Short natural-language description for AI search."
    )

    search_keywords = models.JSONField(
        default=list,
        blank=True,
        validators=[
            validate_string_list
        ]
    )


    # -------------------------------------------------
    # 7. PUBLISHING AND COPYRIGHT
    # -------------------------------------------------

    status = models.CharField(
        max_length=15,
        choices=Status.choices,
        default=Status.DRAFT
    )

    rights_status = models.CharField(
        max_length=15,
        choices=RightsStatus.choices,
        default=RightsStatus.UNKNOWN
    )

    allow_download = models.BooleanField(
        default=False,
        help_text="Whether downloading is permitted for this song."
    )


    # -------------------------------------------------
    # 8. OWNERSHIP AND TIMESTAMPS
    # -------------------------------------------------

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="uploaded_songs"
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )


    # -------------------------------------------------
    # 9. MODEL CONFIGURATION
    # -------------------------------------------------

    class Meta:

        ordering = ["title"]

        verbose_name = "Song"
        verbose_name_plural = "Songs"

        indexes = [

            models.Index(
                fields=["status", "release_date"],
                name="song_status_release_idx"
            ),

            models.Index(
                fields=["title"],
                name="song_title_idx"
            ),

        ]


    # -------------------------------------------------
    # 10. CUSTOM METHODS
    # -------------------------------------------------

    def save(self, *args, **kwargs):

        # Generate a unique slug only once.
        if not self.slug:

            base_slug = (
                slugify(
                    self.title,
                    allow_unicode=True
                )[:190]
                or "song"
            )

            unique_suffix = uuid.uuid4().hex[:12]

            self.slug = f"{base_slug}-{unique_suffix}"

        super().save(*args, **kwargs)


    def __str__(self):

        return self.title
