from django import forms
from .models import ProductReview


PERSIAN_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def normalize_digits(value: str) -> str:
    return (value or "").translate(PERSIAN_DIGITS).strip()


class ProductReviewForm(forms.ModelForm):
    """Review form. New/edited reviews remain pending until an admin approves them."""

    class Meta:
        model = ProductReview
        fields = ("rating", "title", "comment")
        widgets = {
            "rating": forms.Select(choices=[(n, f"{n} از ۵") for n in range(5, 0, -1)]),
            "title": forms.TextInput(attrs={"maxlength": 150, "placeholder": "عنوان کوتاه نظر"}),
            "comment": forms.Textarea(attrs={"rows": 4, "maxlength": 4000, "placeholder": "تجربه‌ات از این کالا را بنویس..."}),
        }


class CheckoutForm(forms.Form):
    """Customer details only; prices and stock are always reloaded from the database."""

    full_name = forms.CharField(max_length=150, strip=True, label="نام و نام خانوادگی")
    phone = forms.CharField(max_length=20, strip=True, label="شماره موبایل")
    city = forms.CharField(max_length=120, strip=True, label="استان و شهر")
    address = forms.CharField(max_length=1000, strip=True, label="نشانی کامل", widget=forms.Textarea)
    postal_code = forms.CharField(max_length=10, required=False, strip=True, label="کد پستی")
    note = forms.CharField(max_length=500, required=False, strip=True, label="یادداشت سفارش")
    payment_method = forms.ChoiceField(
        choices=(("online", "پرداخت آنلاین"),),
        initial="online",
        label="روش پرداخت",
    )
    cart_payload = forms.CharField(widget=forms.HiddenInput, label="سبد خرید")

    def clean_phone(self):
        phone = normalize_digits(self.cleaned_data["phone"])
        compact = phone.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if compact.startswith("+98"):
            compact = "0" + compact[3:]
        elif compact.startswith("98") and len(compact) == 12:
            compact = "0" + compact[2:]
        if not (len(compact) == 11 and compact.startswith("09") and compact.isdigit()):
            raise forms.ValidationError("شماره موبایل معتبر وارد کن؛ نمونه: 09123456789")
        return compact

    def clean_postal_code(self):
        postal_code = normalize_digits(self.cleaned_data.get("postal_code", ""))
        if postal_code and (len(postal_code) != 10 or not postal_code.isdigit()):
            raise forms.ValidationError("کد پستی باید دقیقاً ۱۰ رقم باشد.")
        return postal_code
