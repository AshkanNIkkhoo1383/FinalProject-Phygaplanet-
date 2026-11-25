from django.urls import path
from . import views

app_name = "shop_memory_admin"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("memories/", views.product_memories, name="product_memories"),
    path("knowledge/", views.knowledge_list, name="knowledge_list"),
    path("knowledge/new/", views.knowledge_create, name="knowledge_create"),
    path("knowledge/ai-draft/", views.knowledge_ai_draft, name="knowledge_ai_draft"),
    path("knowledge/<int:pk>/edit/", views.knowledge_edit, name="knowledge_edit"),
    path("knowledge/<int:pk>/delete/", views.knowledge_delete, name="knowledge_delete"),
    path("requested-products/", views.requested_products, name="requested_products"),
    path("handoffs/", views.handoffs, name="handoffs"),
    path("handoffs/<int:pk>/", views.handoff_update, name="handoff_update"),
    path("llm/", views.llm_configurations, name="llm_configurations"),
    path("llm/new/", views.llm_create, name="llm_create"),
    path("llm/<int:pk>/edit/", views.llm_edit, name="llm_edit"),
    path("llm/<int:pk>/test/", views.llm_test, name="llm_test"),
]
