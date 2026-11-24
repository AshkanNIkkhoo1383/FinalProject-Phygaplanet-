
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
)
from django.db.models import Q
from decimal import Decimal 
import uuid
from django.conf import settings

class HumanHandoffRequest(models.Model):

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        IN_PROGRESS = "in_progress", "In Progress"
        RESOLVED = "resolved", "Resolved"
        CLOSED = "closed", "Closed"

    class Reason(models.TextChoices):
        OUT_OF_SCOPE = "out_of_scope", "Out of Scope"
        NEEDS_HUMAN = "needs_human", "Needs Human Review"

    # Public tracking identifier
    reference_id = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        editable=False
    )

    # User who sent the request
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shop_handoff_requests"
    )

    # Session of an anonymous or authenticated user
    session_key = models.CharField(
        max_length=100,
        blank=True
    )

    # Original user message
    user_message = models.TextField()

    reason = models.CharField(
        max_length=30,
        choices=Reason.choices
    )

    # Explanation returned by the scope classifier
    classification_reason = models.CharField(
        max_length=300,
        blank=True
    )

    # Request status
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING
    )

    # Admin responsible for handling the request
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_shop_handoffs"
    )

    # Admin's response or internal notes
    admin_note = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    resolved_at = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return f"Handoff {self.reference_id}"

    class Meta:
        verbose_name = "Human Handoff Request"
        verbose_name_plural = "Human Handoff Requests"

        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["status", "created_at"]
            ),
            models.Index(
                fields=["reason", "created_at"]
            ),
            models.Index(
                fields=["user", "created_at"]
            ),
        ]

class LLMConfiguration(models.Model):

    class Provider(models.TextChoices):
        OLLAMA = "ollama", "Local Ollama"
        OPENAI_COMPATIBLE = (
            "openai_compatible",
            "OpenAI-compatible API"
        )

    name = models.CharField(
        max_length=100,
        default="Mike LLM"
    )

    provider = models.CharField(
        max_length=30,
        choices=Provider.choices,
        default=Provider.OLLAMA
    )

    # Examples:
    # qwen3:1.7b
    # qwen3:4b
    # gpt-4.1-mini (depending on API provider)

    model_name = models.CharField(
        max_length=150,
        default="qwen3:1.7b"
    )

    # For Ollama:
    # http://127.0.0.1:11434/v1
    #
    # For a cloud provider:
    # https://api.example.com/v1

    base_url = models.URLField(
        max_length=300,
        default="http://127.0.0.1:11434/v1"
    )

    # Store the ENV variable NAME, not the API secret itself.
    api_key_env = models.CharField(
        max_length=100,
        blank=True,
        default="SHOP_LLM_API_KEY"
    )

    temperature = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=Decimal("0.30"),
        validators=[
            MinValueValidator(Decimal("0")),
            MaxValueValidator(Decimal("2")),
        ]
    )

    max_output_tokens = models.PositiveSmallIntegerField(
        default=400,
        validators=[
            MinValueValidator(64),
            MaxValueValidator(2048),
        ]
    )

    timeout_seconds = models.PositiveSmallIntegerField(
        default=90,
        validators=[
            MinValueValidator(10),
            MaxValueValidator(300),
        ]
    )

    is_active = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"{self.name} ({self.model_name})"

    class Meta:
        verbose_name = "LLM Configuration"
        verbose_name_plural = "LLM Configurations"

        constraints = [
            models.UniqueConstraint(
                fields=["is_active"],
                condition=Q(is_active=True),
                name="one_active_shop_llm_configuration"
            )
        ]

# =====================================================
# 1. Product Memory
# =====================================================

class ProductMemory(models.Model):

    class IndexStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    # ارتباط یک‌به‌یک با محصول اصلی در اپلیکیشن shop
    product = models.OneToOneField(
        "shop.Product",
        on_delete=models.CASCADE,
        related_name="memory_record"
    )

    # متن آماده‌شده برای جست‌وجوی معنایی
    searchable_text = models.TextField(
        blank=True
    )

    # خلاصه محصول برای ارسال به LLM
    summary = models.TextField(
        blank=True
    )

    # کلیدواژه‌های مرتبط با محصول
    keywords = models.JSONField(
        default=list,
        blank=True
    )

    # ویژگی‌های استخراج‌شده از اطلاعات محصول
    extracted_attributes = models.JSONField(
        default=dict,
        blank=True
    )

    # بردار معنایی محصول
    embedding = models.JSONField(
        default=list,
        blank=True
    )

    embedding_model = models.CharField(
        max_length=150,
        blank=True
    )

    # وضعیت آماده‌سازی اطلاعات برای جست‌وجو
    index_status = models.CharField(
        max_length=20,
        choices=IndexStatus.choices,
        default=IndexStatus.PENDING
    )

    # برای تشخیص تغییر اطلاعات محصول
    content_hash = models.CharField(
        max_length=64,
        blank=True
    )

    indexed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def __str__(self):
        return f"Memory: {self.product.name}"

    class Meta:
        verbose_name = "Product Memory"
        verbose_name_plural = "Product Memories"
        ordering = ["-updated_at"]
# Memory Management Fields

MEMORY_LEVELS = [
    ("frequent", "Frequent"),
    ("normal", "Normal"),
    ("low", "Low"),
]

admin_importance = models.PositiveSmallIntegerField(
    default=3,
    validators=[
        MinValueValidator(1),
        MaxValueValidator(5),
    ]
)

access_count = models.PositiveBigIntegerField(
    default=0
)

last_accessed_at = models.DateTimeField(
    null=True,
    blank=True
)

importance_score = models.PositiveSmallIntegerField(
    default=0,
    validators=[
        MinValueValidator(0),
        MaxValueValidator(100),
    ]
)

memory_level = models.CharField(
    max_length=20,
    choices=MEMORY_LEVELS,
    default="normal"
)

is_protected = models.BooleanField(
    default=False
)
# =====================================================
# 2. Knowledge Document
# =====================================================

class KnowledgeDocument(models.Model):

    class KnowledgeType(models.TextChoices):
        FAQ = "faq", "Frequently Asked Question"
        ADVICE = "advice", "Shopping Advice"
        RECOMMENDATION = "recommendation", "Recommendation"
        GUIDE = "guide", "Product Guide"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PUBLISHED = "published", "Published"
        ARCHIVED = "archived", "Archived"

    knowledge_type = models.CharField(
        max_length=20,
        choices=KnowledgeType.choices
    )

    title = models.CharField(
        max_length=200
    )

    # بیشتر برای FAQ کاربرد دارد
    question = models.TextField(
        blank=True
    )

    answer = models.TextField(
        blank=True
    )

    # محتوای اصلی مشاوره، توصیه یا راهنما
    content = models.TextField(
        blank=True
    )

    # کلیدواژه‌ها و موضوعات مرتبط
    tags = models.JSONField(
        default=list,
        blank=True
    )

    # منبع اطلاعات
    source = models.CharField(
        max_length=200,
        blank=True
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT
    )

    # میزان اهمیت سند برای بازیابی
    priority = models.PositiveSmallIntegerField(
        default=1
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def get_rag_text(self):

        if self.knowledge_type == self.KnowledgeType.FAQ:
            return (
                f"Question: {self.question}\n"
                f"Answer: {self.answer}"
            )

        return self.content

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Knowledge Document"
        verbose_name_plural = "Knowledge Documents"
        ordering = ["-priority", "-updated_at"]
admin_importance = models.PositiveSmallIntegerField(
    default=3,
    validators=[
        MinValueValidator(1),
        MaxValueValidator(5),
    ]
)

access_count = models.PositiveBigIntegerField(
    default=0
)

last_accessed_at = models.DateTimeField(
    null=True,
    blank=True
)

importance_score = models.PositiveSmallIntegerField(
    default=0,
    validators=[
        MinValueValidator(0),
        MaxValueValidator(100),
    ]
)

memory_level = models.CharField(
    max_length=20,
    choices=MEMORY_LEVELS,
    default="normal"
)

is_protected = models.BooleanField(
    default=True
)
# =====================================================
# 3. Knowledge Chunk
# =====================================================

class KnowledgeChunk(models.Model):

    document = models.ForeignKey(
        KnowledgeDocument,
        on_delete=models.CASCADE,
        related_name="chunks"
    )

    # شماره قطعه در سند اصلی
    chunk_index = models.PositiveIntegerField()

    # متن مستقل هر قطعه
    content = models.TextField()

    # بردار معنایی قطعه
    embedding = models.JSONField(
        default=list,
        blank=True
    )

    embedding_model = models.CharField(
        max_length=150,
        blank=True
    )

    # وضعیت تبدیل به بردار
    is_embedded = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"{self.document.title} - "
            f"Chunk {self.chunk_index}"
        )

    class Meta:
        verbose_name = "Knowledge Chunk"
        verbose_name_plural = "Knowledge Chunks"

        ordering = ["document", "chunk_index"]

        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"],
                name="unique_knowledge_document_chunk"
            )
        ]

        indexes = [
            models.Index(
                fields=["document", "chunk_index"]
            ),

            models.Index(
                fields=["is_embedded"]
            )
        ]
access_count = models.PositiveBigIntegerField(
    default=0
)

last_accessed_at = models.DateTimeField(
    null=True,
    blank=True
)
# =====================================================
# 4. Requested Product
# =====================================================

class RequestedProduct(models.Model):

    class DemandLevel(models.TextChoices):
        FREQUENT = "frequent", "Frequently Requested"
        NORMAL = "normal", "Normally Requested"
        LOW = "low", "Low Demand"

    class ResolutionStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        ADDED = "added", "Added to Shop"
        REJECTED = "rejected", "Not Planned"

    # شناسه یکتای درخواست نرمال‌شده
    request_key = models.SlugField(
        max_length=180,
        unique=True
    )

    requested_name = models.CharField(
        max_length=200
    )

    artist_name = models.CharField(
        max_length=200,
        blank=True
    )

    requested_type = models.CharField(
        max_length=50,
        blank=True
    )

    description = models.TextField(
        blank=True
    )

    # اگر کالا بعداً وارد فروشگاه شد،
    # می‌توانیم آن را به محصول اصلی متصل کنیم.
    matched_product = models.ForeignKey(
        "shop.Product",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="memory_requests"
    )

    # تعداد درخواست‌ها از ابتدا
    total_requests = models.PositiveIntegerField(
        default=0
    )

    # تعداد درخواست‌ها در ۳۰ روز گذشته
    requests_last_30_days = models.PositiveIntegerField(
        default=0
    )

    # سطح تقاضا
    demand_level = models.CharField(
        max_length=20,
        choices=DemandLevel.choices,
        default=DemandLevel.LOW
    )

    resolution_status = models.CharField(
        max_length=20,
        choices=ResolutionStatus.choices,
        default=ResolutionStatus.PENDING
    )

    first_requested_at = models.DateTimeField(
        auto_now_add=True
    )

    last_requested_at = models.DateTimeField(
        default=timezone.now
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    def update_demand_level(self):

        if (
            self.admin_importance >= 5
            or self.requests_last_30_days >= 10
        ):
            self.demand_level = self.DemandLevel.FREQUENT

        elif (
            self.admin_importance >= 3
            or self.requests_last_30_days >= 3
        ):
            self.demand_level = self.DemandLevel.NORMAL

        else:
            self.demand_level = self.DemandLevel.LOW

    def save(self, *args, **kwargs):

        self.update_demand_level()

        super().save(*args, **kwargs)

    
    def __str__(self):
        return self.requested_name

    class Meta:

        verbose_name = "Requested Product"
        verbose_name_plural = "Requested Products"

        ordering = [
            "-requests_last_30_days",
            "-total_requests"
        ]

        indexes = [
            models.Index(
                fields=["demand_level", "requests_last_30_days"]
            ),

            models.Index(
                fields=["last_requested_at"]
            )
        ]
admin_importance = models.PositiveSmallIntegerField(
    default=3,
    validators=[
        MinValueValidator(1),
        MaxValueValidator(5),
    ]
)

is_protected = models.BooleanField(
    default=False
)
# =====================================================
# 5. Product Request Event
# =====================================================

class ProductRequestEvent(models.Model):

    class RequestSource(models.TextChoices):
        AI_CHAT = "ai_chat", "AI Chat"
        SEARCH = "search", "Search"
        MANUAL = "manual", "Manual Request"

    requested_product = models.ForeignKey(
        RequestedProduct,
        on_delete=models.CASCADE,
        related_name="request_events"
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="shop_product_requests"
    )

    # جمله‌ای که کاربر واقعاً وارد کرده است
    raw_query = models.TextField(
        blank=True
    )

    source = models.CharField(
        max_length=20,
        choices=RequestSource.choices,
        default=RequestSource.AI_CHAT
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return (
            f"Request for "
            f"{self.requested_product.requested_name}"
        )

    class Meta:

        verbose_name = "Product Request Event"
        verbose_name_plural = "Product Request Events"

        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["requested_product", "created_at"]
            ),

            models.Index(
                fields=["user", "created_at"]
            )
        ]
