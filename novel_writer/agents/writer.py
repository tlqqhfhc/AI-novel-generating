from .base import BaseAgent
from ..context.prompts import WRITER_SYSTEM, WRITER_USER_TEMPLATE


class WriterAgent(BaseAgent):
    """Writes novel chapters based on outline and context."""

    def __init__(self, client, model, temperature=0.9):
        super().__init__(client, model, WRITER_SYSTEM, temperature=temperature)

    def write_chapter(self, context: dict) -> str:
        user_msg = WRITER_USER_TEMPLATE.format(**context)
        return self.call(user_msg)
