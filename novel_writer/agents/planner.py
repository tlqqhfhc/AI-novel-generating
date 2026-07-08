from .base import BaseAgent
from ..context.prompts import PLANNER_SYSTEM, PLANNER_USER_TEMPLATE


class PlannerAgent(BaseAgent):
    """Generates the full novel outline."""

    def __init__(self, client, model, temperature=0.8):
        super().__init__(client, model, PLANNER_SYSTEM, temperature=temperature)

    def plan_novel(self, title, genre, language, premise, extra_requirements="", num_chapters=20) -> dict:
        user_msg = PLANNER_USER_TEMPLATE.format(
            title=title,
            genre=genre,
            language=language,
            premise=premise,
            extra_requirements=extra_requirements,
            num_chapters=num_chapters,
        )
        return self.call_json(user_msg)
