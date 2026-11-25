from django import forms
from django.contrib.auth import get_user_model

from shop_memory.models import (
    KnowledgeDocument,
    HumanHandoffRequest,
    LLMConfiguration,
)


class KnowledgeDocumentForm(forms.ModelForm):
    tags_text = forms.CharField(
        label="برچسب‌ها",
        required=False,
        widget=forms.Textarea(attrs={
            "rows": 2,
            "placeholder": "مثلاً: Rock, Vinyl, Gift",
        }),
        help_text="برچسب‌ها را با کاما جدا کن.",
    )

    class Meta:
        model = KnowledgeDocument
        fields = [
            "title", "knowledge_type", "question", "answer",
            "content", "source", "priority", 
            "status", 
        ]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "عنوان دانش"}),
            "question": forms.Textarea(attrs={"rows": 3}),
            "answer": forms.Textarea(attrs={"rows": 4}),
            "content": forms.Textarea(attrs={"rows": 7}),
            "source": forms.TextInput(attrs={"placeholder": "منبع یا مرجع اطلاعات، در صورت وجود"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields["tags_text"].initial = ", ".join(self.instance.tags or [])

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("knowledge_type")
        if kind == KnowledgeDocument.KnowledgeType.FAQ:
            if not cleaned.get("question", "").strip():
                self.add_error("question", "برای FAQ نوشتن سؤال الزامی است.")
            if not cleaned.get("answer", "").strip():
                self.add_error("answer", "برای FAQ نوشتن پاسخ الزامی است.")
        elif not cleaned.get("content", "").strip():
            self.add_error("content", "برای راهنما، مشاوره یا توصیه، متن محتوا الزامی است.")
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=False)
        obj.tags = [
            item.strip() for item in self.cleaned_data.get("tags_text", "").split(",")
            if item.strip()
        ][:30]
        if commit:
            obj.save()
        return obj


class HandoffUpdateForm(forms.ModelForm):
    class Meta:
        model = HumanHandoffRequest
        fields = ["status", "assigned_to", "admin_note"]
        widgets = {
            "admin_note": forms.Textarea(attrs={"rows": 5, "placeholder": "یادداشت داخلی برای تیم پشتیبانی..."}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        User = get_user_model()
        self.fields["assigned_to"].queryset = User.objects.filter(is_staff=True).order_by("username")
        self.fields["assigned_to"].required = False


class LLMConfigurationForm(forms.ModelForm):
    class Meta:
        model = LLMConfiguration
        fields = [
            "name", "provider", "model_name", "base_url", "api_key_env",
            "temperature", "max_output_tokens", "timeout_seconds", "is_active",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "مثلاً Mike Local Qwen"}),
            "model_name": forms.TextInput(attrs={"placeholder": "qwen3:1.7b"}),
            "base_url": forms.URLInput(attrs={"placeholder": "http://127.0.0.1:11434/v1"}),
            "api_key_env": forms.TextInput(attrs={"placeholder": "SHOP_LLM_API_KEY"}),
        }

    def clean(self):
        cleaned = super().clean()
        provider = cleaned.get("provider")
        api_key_env = cleaned.get("api_key_env")
        if provider == LLMConfiguration.Provider.OPENAI_COMPATIBLE and not api_key_env:
            self.add_error("api_key_env", "برای API باید نام متغیر محیطی کلید را وارد کنی.")
        return cleaned
