
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render, redirect
from django.db import transaction
from .models import UserProfile
from .forms import (
    RegisterForm,
    StyledAuthenticationForm,
    ProfileUpdateForm,
    UserProfileForm,
)


def register_view(request):

    if request.user.is_authenticated:
        return redirect("accounts:profile")

    if request.method == "POST":
        form = RegisterForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                user = form.save()

            login(request, user)

            messages.success(
                request,
                "حساب کاربری شما با موفقیت ساخته شد."
            )

            return redirect("accounts:profile")

    else:
        form = RegisterForm()

    return render(
        request,
        "accounts/register.html",
        {"form": form}
    )


class AccountLoginView(LoginView):

    template_name = "accounts/login.html"
    authentication_form = StyledAuthenticationForm
    redirect_authenticated_user = True


class AccountLogoutView(LogoutView):
    next_page = "accounts:login"


@login_required
def profile_view(request):

    profile, _ = UserProfile.objects.get_or_create(
    user=request.user
)

    if request.method == "POST":
        user_form = ProfileUpdateForm(
            request.POST,
            instance=request.user
        )

        profile_form = UserProfileForm(
            request.POST,
            instance=profile
        )

        if user_form.is_valid() and profile_form.is_valid():
            with transaction.atomic():
                user_form.save()
                profile_form.save()

            messages.success(
                request,
                "اطلاعات پروفایل به‌روزرسانی شد."
            )

            return redirect("accounts:profile")

    else:
        user_form = ProfileUpdateForm(instance=request.user)
        profile_form = UserProfileForm(instance=profile)

    return render(
        request,
        "accounts/profile.html",
        {
            "user_form": user_form,
            "profile_form": profile_form,
        }
    )

