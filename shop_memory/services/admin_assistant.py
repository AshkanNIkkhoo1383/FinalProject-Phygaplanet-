
import json
import re

from shop_memory.services.llm_client import LLMClient


class AdminKnowledgeAssistant:

    ALLOWED_TYPES = {
        "faq",
        "advice",
        "recommendation",
        "guide",
    }

    @classmethod
    def draft_knowledge(
        cls,
        raw_text,
        knowledge_type="advice"
    ):

        # --------------------------------------
        # 1. Validate input
        # --------------------------------------

        if not isinstance(raw_text, str) or not raw_text.strip():
            raise ValueError(
                "Admin content cannot be empty."
            )

        if knowledge_type not in cls.ALLOWED_TYPES:
            raise ValueError(
                "Invalid knowledge type."
            )

        # --------------------------------------
        # 2. System Prompt
        # --------------------------------------

        system_prompt = """
You are the knowledge organizer for Mike,
the shop assistant of PhygaPlanet.

Your task is to organize administrator-provided
information into a structured knowledge document.

Rules:

- Do not invent facts.
- Do not introduce product prices.
- Preserve the original meaning.
- Use only the information supplied by the administrator.
- Return valid JSON only.
- Do not include Markdown code fences.
- Do not add explanations outside JSON.

Required JSON structure:

{
    "title": "Short title",
    "question": "",
    "answer": "",
    "content": "",
    "tags": [],
    "priority": 3,
    "admin_importance": 3
}

For FAQ:
Fill question and answer.

For advice, recommendation or guide:
Fill content.

Priority must be between 1 and 5.
Admin importance must be between 1 and 5.
"""

        # --------------------------------------
        # 3. User Prompt
        # --------------------------------------

        user_prompt = f"""
Knowledge type: {knowledge_type}

Administrator's original information:

{raw_text}

Convert this information into the requested JSON.
"""

        # --------------------------------------
        # 4. Call LLM
        # --------------------------------------

        response = LLMClient.chat(
            [
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_prompt
                }
            ],
            temperature=0.1,
            max_output_tokens=500
        )

        # --------------------------------------
        # 5. Clean LLM Response
        # --------------------------------------

        response = response.strip()

        # Remove Qwen thinking blocks if present.
        response = re.sub(
            r"<think>.*?</think>",
            "",
            response,
            flags=re.DOTALL
        ).strip()

        # Remove Markdown JSON fences.
        response = re.sub(
            r"^```(?:json)?\s*|\s*```$",
            "",
            response
        ).strip()

        # --------------------------------------
        # 6. Parse JSON
        # --------------------------------------

        try:

            data = json.loads(response)

        except json.JSONDecodeError as exc:

            raise ValueError(
                "The LLM did not return valid JSON."
            ) from exc

        if not isinstance(data, dict):
            raise ValueError(
                "Invalid knowledge structure."
            )

        # --------------------------------------
        # 7. Validate Generated Fields
        # --------------------------------------

        title = data.get("title", "")

        if not isinstance(title, str) or not title.strip():
            raise ValueError(
                "Generated title is missing."
            )

        tags = data.get("tags", [])

        if not isinstance(tags, list):
            tags = []

        tags = [
            tag.strip()
            for tag in tags
            if isinstance(tag, str) and tag.strip()
        ][:20]

        priority = data.get("priority", 3)
        importance = data.get("admin_importance", 3)

        try:
            priority = max(1, min(5, int(priority)))
            importance = max(1, min(5, int(importance)))

        except (ValueError, TypeError):
            priority = 3
            importance = 3

        # --------------------------------------
        # 8. Prepare Admin Memory Payload
        # --------------------------------------

        payload = {
            "action": "add_knowledge",

            "knowledge_type": knowledge_type,

            "title": title.strip(),

            "question": data.get("question", "")
                if knowledge_type == "faq" else "",

            "answer": data.get("answer", "")
                if knowledge_type == "faq" else "",

            "content": data.get("content", "")
                if knowledge_type != "faq" else "",

            "tags": tags,

            "priority": priority,

            "admin_importance": importance,

            # Admin must review this draft.
            "status": "draft",

            "is_protected": True,
        }

        if knowledge_type == "faq":

            if not (
                payload["question"].strip()
                and payload["answer"].strip()
            ):
                raise ValueError(
                    "Generated FAQ question or answer is empty."
                )

        elif not payload["content"].strip():

            raise ValueError(
                "Generated knowledge content is empty."
            )

        return payload
