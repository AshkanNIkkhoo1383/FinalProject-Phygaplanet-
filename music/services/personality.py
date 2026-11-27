from music.models_extra import UserMusicProfile

FEATURE_LABELS = {
    "energy": "انرژی موسیقی",
    "danceability": "ریتم و رقص‌پذیری",
    "valence": "حال‌وهوای مثبت آهنگ",
    "acousticness": "آکوستیک بودن",
    "instrumentalness": "بی‌کلام بودن",
}


def calculate_music_match(user, song):
    """Return a transparent taste-fit estimate, or None when profile data is insufficient."""
    if not getattr(user, "is_authenticated", False):
        return None
    try:
        profile = user.music_profile
    except UserMusicProfile.DoesNotExist:
        return None

    parts = []  # (score 0..1, weight, explanation)
    preferred_ids = set(profile.preferred_genres.values_list("id", flat=True))
    song_genres = list(song.genres.all())
    song_genre_ids = {g.id for g in song_genres}
    if preferred_ids and song_genre_ids:
        overlap = bool(preferred_ids & song_genre_ids)
        parts.append((1.0 if overlap else 0.0, 0.30,
                      "ژانر این آهنگ در میان ژانرهای انتخابی تو هست" if overlap
                      else "ژانر این آهنگ با ژانرهای انتخابی تو هم‌پوشانی ندارد"))

    feature_scores = []
    for field, label in FEATURE_LABELS.items():
        user_value = getattr(profile, field, None)
        song_value = getattr(song, field, None)
        if user_value is not None and song_value is not None:
            score = 1.0 - min(1.0, abs(float(user_value) - float(song_value)))
            feature_scores.append(score)
            parts.append((score, 0.14, f"{label} به ترجیح ثبت‌شدهٔ تو نزدیک است" if score >= 0.70
                          else f"{label} با ترجیح ثبت‌شدهٔ تو فاصله دارد"))

    mood_matches = set(str(x).strip().casefold() for x in profile.preferred_moods) & \
                   set(str(x).strip().casefold() for x in song.mood_tags)
    if profile.preferred_moods and song.mood_tags:
        mood_union = set(str(x).strip().casefold() for x in profile.preferred_moods) | \
                     set(str(x).strip().casefold() for x in song.mood_tags)
        mood_score = len(mood_matches) / max(1, len(mood_union))
        parts.append((mood_score, 0.10, "حال‌وهوای آهنگ با تگ‌های موردعلاقه‌ات هم‌خوانی دارد"
                      if mood_matches else "تگ حال‌وهوای مشترکی پیدا نشد"))

    activity_matches = set(str(x).strip().casefold() for x in profile.preferred_activities) & \
                       set(str(x).strip().casefold() for x in song.activity_tags)
    if profile.preferred_activities and song.activity_tags:
        activity_union = set(str(x).strip().casefold() for x in profile.preferred_activities) | \
                          set(str(x).strip().casefold() for x in song.activity_tags)
        activity_score = len(activity_matches) / max(1, len(activity_union))
        parts.append((activity_score, 0.10, "برای یکی از فعالیت‌های موردعلاقه‌ات پیشنهاد شده"
                      if activity_matches else "فعالیت مشترکی در تگ‌ها پیدا نشد"))

    # Require at least two independent signals; one genre match alone should not look like certainty.
    independent_signals = int(bool(preferred_ids and song_genre_ids)) + len(feature_scores) + \
                          int(bool(profile.preferred_moods and song.mood_tags)) + \
                          int(bool(profile.preferred_activities and song.activity_tags))
    if independent_signals < 2 or not parts:
        return None

    total_weight = sum(weight for _, weight, _ in parts)
    score = round(100 * sum(value * weight for value, weight, _ in parts) / total_weight)
    reasons = [reason for _, _, reason in sorted(parts, key=lambda item: item[1], reverse=True)[:4]]
    return {
        "score": max(0, min(100, score)),
        "label": "سازگاری بالا" if score >= 80 else "سازگاری متوسط" if score >= 60 else "سازگاری کمتر",
        "reasons": reasons,
        "basis": "ژانر، ویژگی‌های صوتی و تگ‌های سلیقهٔ ثبت‌شده",
    }
