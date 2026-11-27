from django import forms
from music.models import Genre
from music.models_extra import Playlist, UserMusicProfile


class UserMusicProfileForm(forms.ModelForm):
    preferred_moods_text = forms.CharField(
        required=False, label="حال‌وهوای موردعلاقه",
        help_text="عبارت‌ها را با ویرگول جدا کن؛ مثل آرام، پرانرژی، نوستالژیک.",
        widget=forms.TextInput(attrs={"placeholder": "آرام، پرانرژی، نوستالژیک"}),
    )
    preferred_activities_text = forms.CharField(
        required=False, label="موقعیت‌ها و فعالیت‌ها",
        help_text="مثل مطالعه، ورزش، رانندگی، تمرکز.",
        widget=forms.TextInput(attrs={"placeholder": "مطالعه، ورزش، رانندگی"}),
    )

    class Meta:
        model = UserMusicProfile
        fields = [
            "preferred_genres", "energy", "danceability", "valence",
            "acousticness", "instrumentalness",
        ]
        widgets = {
            "preferred_genres": forms.CheckboxSelectMultiple(),
            "energy": forms.NumberInput(attrs={"min": "0", "max": "1", "step": "0.01"}),
            "danceability": forms.NumberInput(attrs={"min": "0", "max": "1", "step": "0.01"}),
            "valence": forms.NumberInput(attrs={"min": "0", "max": "1", "step": "0.01"}),
            "acousticness": forms.NumberInput(attrs={"min": "0", "max": "1", "step": "0.01"}),
            "instrumentalness": forms.NumberInput(attrs={"min": "0", "max": "1", "step": "0.01"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["preferred_moods_text"].initial = ", ".join(self.instance.preferred_moods or [])
            self.fields["preferred_activities_text"].initial = ", ".join(self.instance.preferred_activities or [])

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.preferred_moods = [x.strip() for x in self.cleaned_data.get("preferred_moods_text", "").split(",") if x.strip()]
        instance.preferred_activities = [x.strip() for x in self.cleaned_data.get("preferred_activities_text", "").split(",") if x.strip()]
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class PlaylistForm(forms.ModelForm):
    class Meta:
        model = Playlist
        fields = ["name", "description", "is_public"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "مثلاً شب‌های آرام"}),
            "description": forms.Textarea(attrs={"rows": 3}),
        }
