
import os
import requests

from shop_memory.models import LLMConfiguration


# =====================================================
# Custom Exception
# =====================================================

class LLMClientError(Exception):
    """Raised when an LLM request fails."""
    pass


# =====================================================
# LLM Client
# =====================================================

class LLMClient:

    # -------------------------------------------------
    # Get active LLM configuration
    # -------------------------------------------------

    @staticmethod
    def get_active_config():

        try:
            return LLMConfiguration.objects.get(
                is_active=True
            )

        except LLMConfiguration.DoesNotExist:

            raise LLMClientError(
                "No active LLM configuration was found."
            )

    # -------------------------------------------------
    # Build API endpoint
    # -------------------------------------------------

    @staticmethod
    def build_endpoint(config):

        base_url = config.base_url.strip().rstrip("/")

        if not base_url.endswith("/v1"):
            base_url += "/v1"

        return base_url + "/chat/completions"

    # -------------------------------------------------
    # Complete a chat request
    # -------------------------------------------------

    @classmethod
    def complete(
        cls,
        config,
        messages,
        temperature=None,
        max_output_tokens=None
    ):

        if not isinstance(messages, list) or not messages:

            raise LLMClientError(
                "At least one message is required."
            )

        endpoint = cls.build_endpoint(config)

        headers = {
            "Content-Type": "application/json"
        }

        # ---------------------------------------------
        # API Authentication
        # ---------------------------------------------

        if (
            config.provider
            == LLMConfiguration.Provider.OPENAI_COMPATIBLE
        ):

            if not config.api_key_env:

                raise LLMClientError(
                    "API key environment variable is not configured."
                )

            api_key = os.environ.get(
                config.api_key_env
            )

            if not api_key:

                raise LLMClientError(
                    f"Environment variable "
                    f"{config.api_key_env} is missing."
                )

            headers["Authorization"] = (
                f"Bearer {api_key}"
            )

        elif (
            config.provider
            != LLMConfiguration.Provider.OLLAMA
        ):

            raise LLMClientError(
                "Unsupported LLM provider."
            )

        # ---------------------------------------------
        # Generation Parameters
        # ---------------------------------------------

        selected_temperature = (
            float(config.temperature)
            if temperature is None
            else float(temperature)
        )

        selected_max_tokens = (
            config.max_output_tokens
            if max_output_tokens is None
            else int(max_output_tokens)
        )

        payload = {
            "model": config.model_name,
            "messages": messages,
            "temperature": selected_temperature,
            "max_tokens": selected_max_tokens,
            "stream": False,
        }

        # ---------------------------------------------
        # Send HTTP Request
        # ---------------------------------------------

        try:

            response = requests.post(
                endpoint,
                headers=headers,
                json=payload,
                timeout=config.timeout_seconds
            )

            response.raise_for_status()

            data = response.json()

            content = (
                data["choices"][0]["message"]["content"]
            )

            if not isinstance(content, str):

                raise LLMClientError(
                    "LLM returned an unexpected response."
                )

            content = content.strip()

            if not content:

                raise LLMClientError(
                    "LLM returned an empty response."
                )

            return content

        except requests.exceptions.Timeout:

            raise LLMClientError(
                "LLM request timed out."
            )

        except requests.exceptions.ConnectionError:

            raise LLMClientError(
                "Could not connect to the LLM server."
            )

        except requests.exceptions.HTTPError as exc:

            status_code = (
                exc.response.status_code
                if exc.response is not None
                else "Unknown"
            )

            raise LLMClientError(
                f"LLM server returned HTTP {status_code}."
            )

        except (KeyError, IndexError, ValueError):

            raise LLMClientError(
                "Could not parse the LLM response."
            )

    # -------------------------------------------------
    # Chat using active configuration
    # -------------------------------------------------

    @classmethod
    def chat(
        cls,
        messages,
        temperature=None,
        max_output_tokens=None
    ):

        config = cls.get_active_config()

        return cls.complete(
            config=config,
            messages=messages,
            temperature=temperature,
            max_output_tokens=max_output_tokens
        )
