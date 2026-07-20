from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.shortcuts import render, redirect

from accounts.forms import RegistrationForm
from accounts.models import Profile
from patients.models import Patient
from doctors.models import Doctor
from common.exceptions import HealthPulseException


def register_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    if request.method == "POST":
        form = RegistrationForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            try:
                user = User.objects.create_user(
                    username=data["username"],
                    email=data["email"],
                    password=data["password"],
                    first_name=data["full_name"].split(" ")[0],
                )
                profile = user.profile  # created by the post_save signal
                profile.role = data["role"]
                profile.phone = data["phone"]
                profile.save()

                if data["role"] == Profile.ROLE_DOCTOR:
                    Doctor(
                        django_user_id=user.id,
                        full_name=data["full_name"],
                        email=data["email"],
                        phone=data["phone"],
                        specialization=data.get("specialization") or "General Physician",
                    ).save()
                else:
                    Patient(
                        django_user_id=user.id,
                        full_name=data["full_name"],
                        aadhaar=data["aadhaar"],
                        phone=data["phone"],
                        email=data["email"],
                        gender=data["gender"],
                        dob=data["dob"],
                        address=data.get("address", ""),
                    ).save()

                login(request, user)
                messages.success(request, f"Welcome to HealthPulse, {data['full_name']}!")
                return redirect("core:dashboard")
            except HealthPulseException as exc:
                messages.error(request, exc.message)
            except Exception as exc:  # pragma: no cover - safety net
                messages.error(request, f"Registration failed: {exc}")
        else:
            messages.error(request, "Please fix the errors below.")
    else:
        form = RegistrationForm()

    return render(request, "registration/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("core:dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.POST.get("next") or "core:dashboard"
            return redirect(next_url)
        messages.error(request, "Invalid username or password.")

    return render(request, "registration/login.html")


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect("accounts:login")


@login_required
def update_settings(request):
    profile = request.user.profile
    if request.method == "POST":
        profile.dark_mode = request.POST.get("dark_mode") == "on"
        profile.notify_email = request.POST.get("notify_email") == "on"
        profile.notify_sms = request.POST.get("notify_sms") == "on"
        profile.save()
        messages.success(request, "Settings updated.")
    return redirect("core:dashboard")
