
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import (
    UserCreationForm,
    AuthenticationForm
)

from .models import UserProfile

User = get_user_model()


class RegisterForm(UserCreationForm):

    email = forms.EmailField(
        label="ایمیل",
        widget=forms.EmailInput(attrs={
            "placeholder": "name@example.com",
            "autocomplete": "email"
        })
    )

    first_name = forms.CharField(
        label="نام",
        max_length=150,
        widget=forms.TextInput(attrs={
            "placeholder": "نام شما",
            "autocomplete": "given-name"
        })
    )

    last_name = forms.CharField(
        label="نام خانوادگی",
        max_length=150,
        widget=forms.TextInput(attrs={
            "placeholder": "نام خانوادگی شما",
            "autocomplete": "family-name"
        })
    )

    class Meta:
        model = User
        fields = (
            "username",
            "email",
            "first_name",
            "last_name",
            "password1",
            "password2",
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "این ایمیل قبلاً ثبت شده است."
            )

        return email

    def save(self, commit=True):
        user = super().save(commit=False)

        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]

        if commit:
            user.save()
            UserProfile.objects.get_or_create(user=user)

        return user


class StyledAuthenticationForm(AuthenticationForm):

    username = forms.CharField(
        label="نام کاربری",
        widget=forms.TextInput(attrs={
            "placeholder": "نام کاربری",
            "autocomplete": "username",
            "autofocus": True
        })
    )

    password = forms.CharField(
        label="رمز عبور",
        strip=False,
        widget=forms.PasswordInput(attrs={
            "placeholder": "رمز عبور",
            "autocomplete": "current-password"
        })
    )


class ProfileUpdateForm(forms.ModelForm):

    class Meta:
        model = User
        fields = (
            "first_name",
            "last_name",
            "email",
        )

        labels = {
            "first_name": "نام",
            "last_name": "نام خانوادگی",
            "email": "ایمیل",
        }

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        exists = User.objects.filter(
            email__iexact=email
        ).exclude(pk=self.instance.pk).exists()

        if exists:
            raise forms.ValidationError(
                "این ایمیل قبلاً استفاده شده است."
            )

        return email


class UserProfileForm(forms.ModelForm):

    class Meta:
        model = UserProfile
        fields = ("display_name",)
        labels = {
            "display_name": "نام نمایشی"
        }
