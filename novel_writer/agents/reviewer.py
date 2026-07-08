from .base import BaseAgent
from ..context.prompts import REVIEWER_SYSTEM, REVIEWER_USER_TEMPLATE


class ReviewerAgent(BaseAgent):
    """Reviews chapters for consistency, character voice, and plot holes."""

    def __init__(self, client, model, temperature=0.3):
        super().__init__(client, model, REVIEWER_SYSTEM, temperature=temperature)

    def review_chapter(self, context: dict) -> dict:
        user_msg = REVIEWER_USER_TEMPLATE.format(**context)
        return self.call_json(user_msg)
