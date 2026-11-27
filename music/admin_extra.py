from django.contrib import admin
from music.models_extra import FavoriteSong, MusicInteraction, Playlist, PlaylistSong, UserMusicProfile


@admin.register(UserMusicProfile)
class UserMusicProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "updated_at")
    search_fields = ("user__username", "user__email")
    filter_horizontal = ("preferred_genres",)


@admin.register(MusicInteraction)
class MusicInteractionAdmin(admin.ModelAdmin):
    list_display = ("song", "event", "user", "created_at")
    list_filter = ("event", "created_at")
    search_fields = ("song__title", "user__username", "session_key")
    readonly_fields = ("created_at",)


@admin.register(FavoriteSong)
class FavoriteSongAdmin(admin.ModelAdmin):
    list_display = ("user", "song", "created_at")
    search_fields = ("user__username", "song__title")


class PlaylistSongInline(admin.TabularInline):
    model = PlaylistSong
    extra = 0


@admin.register(Playlist)
class PlaylistAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "is_public", "updated_at")
    list_filter = ("is_public",)
    search_fields = ("name", "user__username")
    inlines = (PlaylistSongInline,)
