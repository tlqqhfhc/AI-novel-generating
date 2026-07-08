from .base import BaseAgent
from ..context.prompts import MEMORY_SYSTEM, MEMORY_USER_TEMPLATE


class MemoryAgent(BaseAgent):
    """Manages story memory: summaries, key events, character development."""

    def __init__(self, client, model, temperature=0.3):
        super().__init__(client, model, MEMORY_SYSTEM, temperature=temperature)

    def update_memory(self, context: dict) -> dict:
        user_msg = MEMORY_USER_TEMPLATE.format(**context)
        return self.call_json(user_msg)
