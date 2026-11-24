
from django.contrib import admin, messages

from .models import LLMConfiguration
from .services.llm_client import (
    LLMClient,
    LLMClientError,
)

from django.contrib import admin

from .models import HumanHandoffRequest


@admin.register(HumanHandoffRequest)
class HumanHandoffRequestAdmin(admin.ModelAdmin):

    list_display = (
        "reference_id",
        "user",
        "reason",
        "status",
        "assigned_to",
        "created_at",
    )

    list_filter = (
        "status",
        "reason",
        "created_at",
    )

    search_fields = (
        "reference_id",
        "user__username",
        "user_message",
        "classification_reason",
    )

    readonly_fields = (
        "reference_id",
        "user",
        "session_key",
        "user_message",
        "reason",
        "classification_reason",
        "created_at",
        "updated_at",
    )

    fieldsets = (
        ("Request Information", {
            "fields": (
                "reference_id",
                "user",
                "session_key",
                "user_message",
                "reason",
                "classification_reason",
            )
        }),

        ("Support Management", {
            "fields": (
                "status",
                "assigned_to",
                "admin_note",
                "resolved_at",
            )
        }),

        ("Timestamps", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )


@admin.register(LLMConfiguration)
class LLMConfigurationAdmin(admin.ModelAdmin):

    list_display = (
        "name",
        "provider",
        "model_name",
        "is_active",
        "updated_at",
    )

    list_filter = (
        "provider",
        "is_active",
    )

    search_fields = (
        "name",
        "model_name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    fieldsets = (
        ("Model", {
            "fields": (
                "name",
                "provider",
                "model_name",
                "is_active",
            )
        }),

        ("Connection", {
            "fields": (
                "base_url",
                "api_key_env",
            )
        }),

        ("Generation Settings", {
            "fields": (
                "temperature",
                "max_output_tokens",
                "timeout_seconds",
            )
        }),

        ("Timestamps", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )

    actions = [
        "test_selected_models",
    ]

    def save_model(self, request, obj, form, change):

        # Deactivate previous configuration first.
        if obj.is_active:

            LLMConfiguration.objects.exclude(
                pk=obj.pk
            ).filter(
                is_active=True
            ).update(
                is_active=False
            )

        super().save_model(
            request,
            obj,
            form,
            change
        )

    @admin.action(description="Test selected LLM configuration")
    def test_selected_models(self, request, queryset):

        for config in queryset:

            try:

                response = LLMClient.complete(
                    config,
                    [
                        {
                            "role": "user",
                            "content": (
                                "Reply with exactly: "
                                "Mike is ready."
                            )
                        }
                    ]
                )

                self.message_user(
                    request,
                    f"{config.model_name}: {response[:120]}",
                    messages.SUCCESS
                )

            except LLMClientError as exc:

                self.message_user(
                    request,
                    f"{config.model_name}: {exc}",
                    messages.ERROR
                )
