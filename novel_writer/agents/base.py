from openai import OpenAI
import json
import time


class BaseAgent:
    """Agent that calls a chat-completion API with retry and JSON parsing."""

    def __init__(self, client: OpenAI, model: str,
                 system_prompt: str = "",
                 max_retries: int = 3,
                 temperature: float = 0.7):
        self.client = client
        self.model = model
        self.system_prompt = system_prompt
        self.max_retries = max_retries
        self.temperature = temperature

    def call(self, user_message: str,
             response_format: str = "text",
             temperature: float | None = None) -> str:
        temp = temperature if temperature is not None else self.temperature
        kwargs = dict(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=temp,
        )
        if response_format == "json_object":
            kwargs["response_format"] = {"type": "json_object"}

        last_error = None
        for attempt in range(self.max_retries):
            try:
                resp = self.client.chat.completions.create(**kwargs)
                content = resp.choices[0].message.content
                return content or ""
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    wait = 2 ** attempt
                    time.sleep(wait)
        raise RuntimeError(f"API call failed after {self.max_retries} retries: {last_error}")

    def call_json(self, user_message: str,
                  temperature: float | None = None) -> dict:
        content = self.call(user_message,
                            response_format="json_object",
                            temperature=temperature)
        content = content.strip()
        if content.startswith("```"):
            start = content.find("{")
            if start == -1:
                start = content.find("[")
            end = content.rfind("}")
            if end == -1:
                end = content.rfind("]")
            if start != -1 and end != -1 and end > start:
                content = content[start:end + 1]
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            raise ValueError(f"Failed to parse JSON from response: {content[:500]}")
