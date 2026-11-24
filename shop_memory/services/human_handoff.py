
from django.contrib.auth import get_user_model

from shop_memory.models import HumanHandoffRequest


User = get_user_model()


class HumanHandoffService:

    OUT_OF_SCOPE_MESSAGE = (
        "درخواست شما خارج از محدوده کاری دستیار "
        "فروشگاه Mike است. Mike فقط در زمینه "
        "محصولات یادگاری موسیقی، مشخصات کالاها، "
        "قیمت، موجودی، مقایسه و راهنمای خرید "
        "این محصولات پاسخ‌گو است. "
        "درخواست شما برای بررسی توسط پشتیبانی ثبت شد."
    )

    NEEDS_HUMAN_MESSAGE = (
        "برای پاسخ‌گویی دقیق به این درخواست، "
        "نیاز به بررسی پشتیبان داریم. "
        "درخواست شما برای بررسی ثبت شد."
    )

    @classmethod
    def create(
        cls,
        user_message,
        decision,
        reason="",
        user=None,
        session_key=""
    ):

        if decision not in (
            "out_of_scope",
            "needs_human"
        ):
            raise ValueError(
                "Invalid handoff decision."
            )

        if decision == "out_of_scope":
            request_reason = (
                HumanHandoffRequest.Reason.OUT_OF_SCOPE
            )
            message = cls.OUT_OF_SCOPE_MESSAGE

        else:
            request_reason = (
                HumanHandoffRequest.Reason.NEEDS_HUMAN
            )
            message = cls.NEEDS_HUMAN_MESSAGE

        if not getattr(user, "is_authenticated", False):
            user = None

        handoff = HumanHandoffRequest.objects.create(
            user=user,
            session_key=session_key or "",
            user_message=user_message[:5000],
            reason=request_reason,
            classification_reason=reason[:300],
        )

        return {
            "answer": (
                f"{message}\n\n"
                f"کد پیگیری: {handoff.reference_id}"
            ),

            "handoff_id": str(
                handoff.reference_id
            ),

            "handoff_status": handoff.status,
        }
