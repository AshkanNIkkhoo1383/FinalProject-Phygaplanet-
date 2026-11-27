from music.models_extra import MusicInteraction


def record_interaction(request, song, event, listened_seconds=0):
    if not request.session.session_key:
        request.session.create()
    user = request.user if request.user.is_authenticated else None
    return MusicInteraction.objects.create(
        user=user,
        song=song,
        event=event,
        session_key=request.session.session_key or "",
        listened_seconds=max(0, int(listened_seconds or 0)),
    )
