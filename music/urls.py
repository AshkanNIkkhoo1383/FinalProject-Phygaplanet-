from django.urls import path
from music import views

app_name = "music"

urlpatterns = [
    path("", views.music_home, name="home"),
    path("songs/", views.song_list, name="song_list"),
    path("genres/<int:genre_id>/", views.song_list, name="genre_songs"),
    path("song/<str:slug>/", views.song_detail, name="song_detail"),
    path("song/<str:slug>/favorite/", views.toggle_favorite, name="toggle_favorite"),
    path("song/<str:slug>/play/", views.track_play, name="track_play"),
    path("song/<str:slug>/stream/", views.song_stream, name="song_stream"),
    path("song/<str:slug>/download/", views.song_download, name="song_download"),
    path("artists/", views.artist_list, name="artist_list"),
    path("artists/<int:pk>/", views.artist_detail, name="artist_detail"),
    path("albums/", views.album_list, name="album_list"),
    path("albums/<int:pk>/", views.album_detail, name="album_detail"),
    path("favorites/", views.favorites, name="favorites"),
    path("history/", views.listening_history, name="history"),
    path("my-taste/", views.taste_profile, name="taste_profile"),
    path("playlists/", views.playlist_list, name="playlist_list"),
    path("playlists/<int:pk>/", views.playlist_detail, name="playlist_detail"),
]
