from pathlib import Path
import mimetypes

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, Q, CharField
from django.db.models.functions import Cast
from django.http import FileResponse, Http404, HttpResponseForbidden, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from music.forms import PlaylistForm, UserMusicProfileForm
from music.models import Album, Artist, Genre, Song
from music.models_extra import FavoriteSong, MusicInteraction, Playlist, PlaylistSong, UserMusicProfile
from music.services.interactions import record_interaction
from music.services.personality import calculate_music_match

PUBLISHED = Song.Status.PUBLISHED
DOWNLOADABLE_RIGHTS = {
    Song.RightsStatus.PLATFORM_OWNED,
    Song.RightsStatus.LICENSED,
    Song.RightsStatus.PUBLIC_DOMAIN,
    Song.RightsStatus.AUTHORIZED,
}


def _published_songs():
    return Song.objects.filter(status=PUBLISHED).select_related("album").prefetch_related("artists", "genres")


def _popular_songs(queryset=None):
    queryset = queryset if queryset is not None else _published_songs()
    return queryset.annotate(
        play_total=Count("interactions", filter=Q(interactions__event=MusicInteraction.Event.PLAY), distinct=True)
    ).order_by("-play_total", "-release_date", "title")


def music_home(request):
    songs = _published_songs()
    context = {
        "genres": Genre.objects.all(),
        "new_songs": songs.order_by("-release_date", "-created_at")[:8],
        "popular_songs": _popular_songs(songs)[:8],
        "featured_artists": Artist.objects.filter(songs__status=PUBLISHED).distinct()[:6],
        "page_title": "سیاره موسیقی تو",
    }
    return render(request, "music/home.html", context)


def song_list(request, genre_id=None):
    songs = _published_songs()
    selected_genre = None
    if genre_id is not None:
        selected_genre = get_object_or_404(Genre, pk=genre_id)
        songs = songs.filter(genres=selected_genre)

    query = request.GET.get("q", "").strip()
    if query:
        songs = songs.annotate(search_keywords_text=Cast("search_keywords", output_field=CharField()))
        songs = songs.filter(
            Q(title__icontains=query) | Q(artists__name__icontains=query) |
            Q(album__title__icontains=query) | Q(description__icontains=query) |
            Q(ai_summary__icontains=query) | Q(search_keywords_text__icontains=query)
        ).distinct()

    selected_genre_filter = request.GET.get("genre", "")
    if selected_genre_filter.isdigit():
        songs = songs.filter(genres__id=int(selected_genre_filter)).distinct()

    sort = request.GET.get("sort", "newest")
    if sort == "popular":
        songs = _popular_songs(songs)
    elif sort == "title":
        songs = songs.order_by("title")
    else:
        songs = songs.order_by("-release_date", "-created_at")

    page_obj = Paginator(songs, 12).get_page(request.GET.get("page"))
    context = {
        "songs": page_obj.object_list,
        "page_obj": page_obj,
        "genres": Genre.objects.all(),
        "query": query,
        "sort": sort,
        "selected_genre": selected_genre,
        "selected_genre_filter": selected_genre_filter,
    }
    return render(request, "music/song_list.html", context)


def song_detail(request, slug):
    song = get_object_or_404(_published_songs(), slug=slug)
    record_interaction(request, song, MusicInteraction.Event.VIEW)
    match = calculate_music_match(request.user, song)
    related = _published_songs().filter(genres__in=song.genres.all()).exclude(pk=song.pk).distinct()[:4]
    if not related:
        related = _published_songs().exclude(pk=song.pk).order_by("-release_date")[:4]

    theme = "default"
    genre_names = " ".join(g.name.casefold() for g in song.genres.all())
    theme_rules = [
        (("metal", "rock", "punk", "راک", "متال", "پانک"), "rock"),
        (("jazz", "blues", "swing", "جاز", "بلوز"), "jazz"),
        (("electronic", "edm", "techno", "house", "ترنس", "الکترونیک", "الکترو"), "electronic"),
        (("classical", "orchestral", "کلاسیک"), "classical"),
        (("hip hop", "hip-hop", "rap", "رپ", "هیپ هاپ", "هیپ‌هاپ"), "hiphop"),
        (("ambient", "chill", "lofi", "lo-fi", "آرام", "امبینت", "چیل", "لوفای"), "ambient"),
        (("pop", "پاپ"), "pop"),
    ]
    for terms, name in theme_rules:
        if any(term in genre_names for term in terms):
            theme = name
            break

    can_download = bool(song.allow_download and song.rights_status in DOWNLOADABLE_RIGHTS and song.audio_file)
    is_favorite = request.user.is_authenticated and FavoriteSong.objects.filter(user=request.user, song=song).exists()
    context = {
        "song": song,
        "match": match,
        "related_songs": related,
        "genre_theme": theme,
        "can_download": can_download,
        "is_favorite": is_favorite,
        "page_title": song.title,
    }
    return render(request, "music/song_detail.html", context)


@require_POST
@login_required
def toggle_favorite(request, slug):
    song = get_object_or_404(Song, slug=slug, status=PUBLISHED)
    favorite, created = FavoriteSong.objects.get_or_create(user=request.user, song=song)
    if created:
        messages.success(request, "آهنگ به علاقه‌مندی‌ها اضافه شد.")
    else:
        favorite.delete()
        messages.info(request, "آهنگ از علاقه‌مندی‌ها حذف شد.")
    return redirect("music:song_detail", slug=song.slug)


@login_required
def favorites(request):
    songs = _published_songs().filter(favorited_by__user=request.user).distinct()
    return render(request, "music/favorites.html", {"songs": songs})


@login_required
def listening_history(request):
    interactions = MusicInteraction.objects.filter(
        user=request.user, event=MusicInteraction.Event.PLAY
    ).select_related("song", "song__album").prefetch_related("song__artists").order_by("-created_at")[:100]
    return render(request, "music/history.html", {"interactions": interactions})


@require_POST
def track_play(request, slug):
    song = get_object_or_404(Song, slug=slug, status=PUBLISHED)
    record_interaction(request, song, MusicInteraction.Event.PLAY)
    return JsonResponse({"ok": True})


def song_stream(request, slug):
    """Serve an authorized published track for in-browser playback."""
    song = get_object_or_404(Song, slug=slug, status=PUBLISHED)
    if song.rights_status not in DOWNLOADABLE_RIGHTS:
        raise Http404("Streaming is not available for this track.")
    if not song.audio_file:
        raise Http404("Audio file is not available.")
    extension = Path(song.audio_file.name).suffix or ".mp3"
    filename = f"{song.slug}{extension}"
    content_type = mimetypes.guess_type(filename)[0] or "audio/mpeg"
    try:
        file_handle = song.audio_file.open("rb")
    except (FileNotFoundError, OSError, ValueError):
        raise Http404("Audio file could not be opened.")
    return FileResponse(file_handle, as_attachment=False, filename=filename, content_type=content_type)


def song_download(request, slug):
    song = get_object_or_404(Song, slug=slug, status=PUBLISHED)
    if not song.allow_download or song.rights_status not in DOWNLOADABLE_RIGHTS:
        raise Http404("Download is not available for this song.")
    if not song.audio_file:
        raise Http404("Audio file is not available.")
    extension = Path(song.audio_file.name).suffix or ".mp3"
    filename = f"{song.slug}{extension}"
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    try:
        file_handle = song.audio_file.open("rb")
    except (FileNotFoundError, OSError, ValueError):
        raise Http404("Audio file could not be opened.")
    record_interaction(request, song, MusicInteraction.Event.DOWNLOAD)
    return FileResponse(file_handle, as_attachment=True, filename=filename, content_type=content_type)


def artist_list(request):
    artists = Artist.objects.filter(songs__status=PUBLISHED).annotate(
        published_song_count=Count("songs", filter=Q(songs__status=PUBLISHED), distinct=True)
    ).distinct()
    query = request.GET.get("q", "").strip()
    if query:
        artists = artists.filter(Q(name__icontains=query) | Q(bio__icontains=query))
    return render(request, "music/artist_list.html", {"artists": artists, "query": query})


def artist_detail(request, pk):
    artist = get_object_or_404(Artist, pk=pk)
    songs = _published_songs().filter(artists=artist)
    return render(request, "music/artist_detail.html", {"artist": artist, "songs": songs})


def album_list(request):
    albums = Album.objects.filter(songs__status=PUBLISHED).annotate(
        published_song_count=Count("songs", filter=Q(songs__status=PUBLISHED), distinct=True)
    ).distinct()
    query = request.GET.get("q", "").strip()
    if query:
        albums = albums.filter(Q(title__icontains=query) | Q(artists__name__icontains=query)).distinct()
    return render(request, "music/album_list.html", {"albums": albums, "query": query})


def album_detail(request, pk):
    album = get_object_or_404(Album, pk=pk)
    songs = _published_songs().filter(album=album)
    return render(request, "music/album_detail.html", {"album": album, "songs": songs})


@login_required
def taste_profile(request):
    profile, _ = UserMusicProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = UserMusicProfileForm(request.POST, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "پروفایل سلیقه موسیقی ذخیره شد.")
            return redirect("music:taste_profile")
    else:
        form = UserMusicProfileForm(instance=profile)
    return render(request, "music/taste_profile.html", {"form": form})


@login_required
def playlist_list(request):
    playlists = Playlist.objects.filter(user=request.user).annotate(song_count=Count("songs", distinct=True))
    if request.method == "POST":
        form = PlaylistForm(request.POST)
        if form.is_valid():
            playlist = form.save(commit=False)
            playlist.user = request.user
            playlist.save()
            messages.success(request, "پلی‌لیست ساخته شد.")
            return redirect("music:playlist_detail", pk=playlist.pk)
    else:
        form = PlaylistForm()
    return render(request, "music/playlist_list.html", {"playlists": playlists, "form": form})


def playlist_detail(request, pk):
    if request.user.is_authenticated:
        visible_playlists = Playlist.objects.filter(Q(is_public=True) | Q(user=request.user))
    else:
        visible_playlists = Playlist.objects.filter(is_public=True)
    playlist = get_object_or_404(visible_playlists, pk=pk)
    is_owner = request.user.is_authenticated and playlist.user_id == request.user.id
    songs = _published_songs().filter(playlists=playlist)
    available_songs = _published_songs().exclude(playlists=playlist)
    if request.method == "POST":
        if not is_owner:
            return HttpResponseForbidden("Only the playlist owner can edit this playlist.")
        song = get_object_or_404(Song, pk=request.POST.get("song_id"), status=PUBLISHED)
        PlaylistSong.objects.get_or_create(playlist=playlist, song=song)
        messages.success(request, "آهنگ به پلی‌لیست اضافه شد.")
        return redirect("music:playlist_detail", pk=playlist.pk)
    return render(request, "music/playlist_detail.html", {
        "playlist": playlist, "songs": songs, "available_songs": available_songs[:40],
        "is_owner": is_owner,
    })
