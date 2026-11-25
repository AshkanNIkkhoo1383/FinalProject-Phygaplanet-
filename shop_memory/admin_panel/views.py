from datetime import timedelta

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from shop_memory.models import (
    ProductMemory,
    KnowledgeDocument,
    KnowledgeChunk,
    RequestedProduct,
    HumanHandoffRequest,
    LLMConfiguration,
)
from shop_memory.manager import ShopMemoryManager
from shop_memory.services.llm_client import LLMClient, LLMClientError
from shop_memory.services.admin_assistant import (
    AdminKnowledgeAssistant
)
from .forms import KnowledgeDocumentForm, HandoffUpdateForm, LLMConfigurationForm

LOGIN_URL = "/admin/login/"


def _paginate(request, queryset, per_page=12):
    return Paginator(queryset, per_page).get_page(request.GET.get("page"))


@staff_member_required(login_url=LOGIN_URL)
def dashboard(request):
    pending_handoffs = HumanHandoffRequest.objects.filter(status=HumanHandoffRequest.Status.PENDING).count()
    context = {
        "product_memory_count": ProductMemory.objects.count(),
        "frequent_count": ProductMemory.objects.filter(memory_level="frequent").count(),
        "normal_count": ProductMemory.objects.filter(memory_level="normal").count(),
        "low_count": ProductMemory.objects.filter(memory_level="low").count(),
        "knowledge_count": KnowledgeDocument.objects.count(),
        "pending_chunks": KnowledgeChunk.objects.filter(is_embedded=False).count(),
        "requested_count": RequestedProduct.objects.count(),
        "pending_handoffs": pending_handoffs,
        "active_llm": LLMConfiguration.objects.filter(is_active=True).first(),
        "recent_handoffs": HumanHandoffRequest.objects.select_related("user").order_by("-created_at")[:6],
        "recent_knowledge": KnowledgeDocument.objects.order_by("-updated_at")[:5],
    }
    return render(request, "shop_memory/admin_panel/dashboard.html", context)


@staff_member_required(login_url=LOGIN_URL)
def product_memories(request):
    queryset = ProductMemory.objects.select_related("product", "product__category").order_by("-importance_score", "-updated_at")
    level = request.GET.get("level", "")
    status = request.GET.get("status", "")
    query = request.GET.get("q", "").strip()
    if level in {"frequent", "normal", "low"}:
        queryset = queryset.filter(memory_level=level)
    if status in {"pending", "ready", "failed"}:
        queryset = queryset.filter(index_status=status)
    if query:
        queryset = queryset.filter(
            Q(product__name__icontains=query)
            | Q(product__artist_name__icontains=query)
            | Q(product__album_name__icontains=query)
            | Q(searchable_text__icontains=query)
        )
    page_obj = _paginate(request, queryset)
    return render(request, "shop_memory/admin_panel/product_memories.html", {
        "page_obj": page_obj, "level": level, "status": status, "q": query,
    })


@staff_member_required(login_url=LOGIN_URL)
def knowledge_list(request):
    queryset = KnowledgeDocument.objects.order_by("-priority", "-updated_at")
    kind = request.GET.get("kind", "")
    status = request.GET.get("status", "")
    query = request.GET.get("q", "").strip()
    if kind:
        queryset = queryset.filter(knowledge_type=kind)
    if status:
        queryset = queryset.filter(status=status)
    if query:
        queryset = queryset.filter(
            Q(title__icontains=query) | Q(question__icontains=query)
            | Q(answer__icontains=query) | Q(content__icontains=query)
        )
    page_obj = _paginate(request, queryset)
    return render(request, "shop_memory/admin_panel/knowledge_list.html", {
        "page_obj": page_obj, "kind": kind, "status": status, "q": query,
    })


@staff_member_required(login_url=LOGIN_URL)
def knowledge_create(request):
    if request.method == "POST":
        form = KnowledgeDocumentForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                document = form.save()
                ShopMemoryManager.rebuild_chunks(document)
                if hasattr(ShopMemoryManager, "_apply_importance"):
                    ShopMemoryManager._apply_importance(document)
                    document.save(update_fields=["importance_score", "memory_level", "updated_at"])
            messages.success(request, "سند دانش ذخیره شد و قطعه‌های RAG ساخته شدند.")
            return redirect("shop_memory_admin:knowledge_list")
    else:
        form = KnowledgeDocumentForm()
    return render(request, "shop_memory/admin_panel/knowledge_form.html", {"form": form, "page_title": "افزودن دانش جدید"})


@staff_member_required(login_url=LOGIN_URL)
def knowledge_ai_draft(request):
    draft = request.session.get("shop_memory_knowledge_draft")
    error = None
    if request.method == "POST":
        action = request.POST.get("action", "generate")
        if action == "confirm" and draft:
            try:
                ShopMemoryManager.process_admin_message(draft)
                request.session.pop("shop_memory_knowledge_draft", None)
                messages.success(request, "پیش‌نویس بررسی و به حافظه دانش اضافه شد.")
                return redirect("shop_memory_admin:knowledge_list")
            except Exception as exc:
                error = str(exc)
        elif action == "discard":
            request.session.pop("shop_memory_knowledge_draft", None)
            messages.info(request, "پیش‌نویس کنار گذاشته شد.")
            return redirect("shop_memory_admin:knowledge_list")
        else:
            raw_text = request.POST.get("raw_text", "").strip()
            kind = request.POST.get("knowledge_type", "advice")
            try:
                draft = AdminKnowledgeAssistant.draft_knowledge(
                    raw_text=raw_text, knowledge_type=kind
                )
                request.session["shop_memory_knowledge_draft"] = draft
            except Exception as exc:
                error = str(exc)
    return render(request, "shop_memory/admin_panel/knowledge_ai_draft.html", {
        "draft": draft, "error": error,
    })


@staff_member_required(login_url=LOGIN_URL)
def knowledge_edit(request, pk):
    document = get_object_or_404(KnowledgeDocument, pk=pk)
    if request.method == "POST":
        form = KnowledgeDocumentForm(request.POST, instance=document)
        if form.is_valid():
            with transaction.atomic():
                document = form.save()
                ShopMemoryManager.rebuild_chunks(document)
                if hasattr(ShopMemoryManager, "_apply_importance"):
                    ShopMemoryManager._apply_importance(document)
                    document.save(update_fields=["importance_score", "memory_level", "updated_at"])
            messages.success(request, "سند دانش و قطعه‌های RAG به‌روزرسانی شدند.")
            return redirect("shop_memory_admin:knowledge_list")
    else:
        form = KnowledgeDocumentForm(instance=document)
    return render(request, "shop_memory/admin_panel/knowledge_form.html", {"form": form, "page_title": "ویرایش سند دانش", "document": document})


@staff_member_required(login_url=LOGIN_URL)
@require_POST
def knowledge_delete(request, pk):
    document = get_object_or_404(KnowledgeDocument, pk=pk)
    document.delete()
    messages.success(request, "سند و قطعه‌های وابسته از حافظه حذف شدند.")
    return redirect("shop_memory_admin:knowledge_list")


@staff_member_required(login_url=LOGIN_URL)
def requested_products(request):
    queryset = RequestedProduct.objects.select_related("matched_product").order_by("-requests_last_30_days", "-total_requests")
    level = request.GET.get("level", "")
    status = request.GET.get("status", "")
    query = request.GET.get("q", "").strip()
    if level:
        queryset = queryset.filter(demand_level=level)
    if status:
        queryset = queryset.filter(resolution_status=status)
    if query:
        queryset = queryset.filter(Q(requested_name__icontains=query) | Q(artist_name__icontains=query))
    return render(request, "shop_memory/admin_panel/requested_products.html", {
        "page_obj": _paginate(request, queryset), "level": level, "status": status, "q": query,
    })


@staff_member_required(login_url=LOGIN_URL)
def handoffs(request):
    queryset = HumanHandoffRequest.objects.select_related("user", "assigned_to").order_by("-created_at")
    status = request.GET.get("status", "")
    if status:
        queryset = queryset.filter(status=status)
    query = request.GET.get("q", "").strip()
    if query:
        queryset = queryset.filter(Q(user_message__icontains=query) | Q(reference_id__icontains=query))
    return render(request, "shop_memory/admin_panel/handoffs.html", {
        "page_obj": _paginate(request, queryset), "status": status, "q": query,
    })


@staff_member_required(login_url=LOGIN_URL)
def handoff_update(request, pk):
    handoff = get_object_or_404(HumanHandoffRequest, pk=pk)
    if request.method == "POST":
        form = HandoffUpdateForm(request.POST, instance=handoff)
        if form.is_valid():
            obj = form.save(commit=False)
            if obj.status == HumanHandoffRequest.Status.RESOLVED and not obj.resolved_at:
                obj.resolved_at = timezone.now()
            elif obj.status != HumanHandoffRequest.Status.RESOLVED:
                obj.resolved_at = None
            obj.save()
            messages.success(request, "وضعیت درخواست پشتیبانی ذخیره شد.")
            return redirect("shop_memory_admin:handoffs")
    else:
        form = HandoffUpdateForm(instance=handoff)
    return render(request, "shop_memory/admin_panel/handoff_update.html", {"form": form, "handoff": handoff})


@staff_member_required(login_url=LOGIN_URL)
def llm_configurations(request):
    configs = LLMConfiguration.objects.order_by("-is_active", "-updated_at")
    return render(request, "shop_memory/admin_panel/llm_configurations.html", {"configs": configs})


@staff_member_required(login_url=LOGIN_URL)
def llm_create(request):
    return _llm_form(request)


@staff_member_required(login_url=LOGIN_URL)
def llm_edit(request, pk):
    config = get_object_or_404(LLMConfiguration, pk=pk)
    return _llm_form(request, config)


def _llm_form(request, instance=None):
    if request.method == "POST":
        form = LLMConfigurationForm(request.POST, instance=instance)
        if form.is_valid():
            with transaction.atomic():
                config = form.save(commit=False)
                if config.is_active:
                    LLMConfiguration.objects.exclude(pk=config.pk).filter(is_active=True).update(is_active=False)
                config.save()
            messages.success(request, "تنظیمات مدل زبانی ذخیره شد.")
            return redirect("shop_memory_admin:llm_configurations")
    else:
        form = LLMConfigurationForm(instance=instance)
    return render(request, "shop_memory/admin_panel/llm_form.html", {
        "form": form,
        "page_title": "ویرایش مدل زبانی" if instance else "افزودن مدل زبانی",
    })


@staff_member_required(login_url=LOGIN_URL)
@require_POST
def llm_test(request, pk):
    config = get_object_or_404(LLMConfiguration, pk=pk)
    try:
        answer = LLMClient.complete(
            config,
            [{"role": "user", "content": "Reply with exactly: Mike is ready."}],
            temperature=0,
            max_output_tokens=40,
        )
        messages.success(request, f"اتصال موفق بود: {answer[:120]}")
    except LLMClientError as exc:
        messages.error(request, f"اتصال ناموفق بود: {exc}")
    return redirect("shop_memory_admin:llm_configurations")
