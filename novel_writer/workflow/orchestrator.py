"""Orchestrator: coordinates the multi-agent novel writing workflow."""

import json
from datetime import datetime

from ..config import get_api_client
from ..db.schema import init_db, get_connection
from ..db import repository as repo
from ..agents.planner import PlannerAgent
from ..agents.writer import WriterAgent
from ..agents.reviewer import ReviewerAgent
from ..agents.memory import MemoryAgent
from ..context import builder as ctx_builder
from ..context.prompts import (
    REVISER_SYSTEM,
    REVISER_USER_TEMPLATE,
    CONSISTENCY_SYSTEM,
    CONSISTENCY_USER_TEMPLATE,
)
from ..agents.base import BaseAgent


_REVISION_THRESHOLD = 65
_MAX_REVISIONS = 2


class Orchestrator:
    """Drives the novel-writing workflow with minimal-context discipline."""

    def __init__(self, config: dict):
        self.config = config
        self.client = get_api_client(config)
        self.model = config.get("model", "deepseek-chat")
        self.db_path = config.get("db_path", "./novel_writer.db")
        self.conn = get_connection(self.db_path)
        init_db(self.db_path)

        self.planner = PlannerAgent(self.client, self.model)
        self.writer = WriterAgent(self.client, self.model)
        self.reviewer = ReviewerAgent(self.client, self.model)
        self.memory = MemoryAgent(self.client, self.model)

    # --- Novel Management --------------------------------------------------------------

    def create_novel(self, title, genre="", language="zh", premise="",
                     style_guide="", target_audience="",
                     word_count_goal=0) -> int:
        novel_id = repo.create_novel(
            self.conn, title, genre, language, premise,
            style_guide, target_audience, word_count_goal
        )
        print(f"  Created novel: {title} (ID: {novel_id})")
        return novel_id

    def get_novel(self, novel_id):
        return repo.get_novel(self.conn, novel_id)

    def list_novels(self):
        return repo.list_novels(self.conn)

    def show_novel_status(self, novel_id):
        novel = repo.get_novel(self.conn, novel_id)
        if not novel:
            print("  Novel not found")
            return

        chapters = repo.get_novel_chapters(self.conn, novel_id)
        chars = repo.get_novel_characters(self.conn, novel_id)
        threads = repo.get_novel_plot_threads(self.conn, novel_id)

        print(f"\n{'='*60}")
        print(f"  Title: {novel['title']}")
        print(f"  Genre: {novel['genre']} | Lang: {novel['language']}")
        print(f"  Created: {novel['created_at']}")
        print(f"{'='*60}")

        print(f"\n  Characters ({len(chars)}):")
        for c in chars:
            print(f"    - {c['name']} ({c['role']})")

        print(f"\n  Chapters ({len(chapters)}):")
        status_counts = {}
        for ch in chapters:
            status_counts[ch['status']] = status_counts.get(ch['status'], 0) + 1
            icon = {"outlined": " ", "writing": ">", "written": "x",
                    "reviewing": "~", "reviewed": "o", "finalized": "*"}.get(ch['status'], " ")
            print(f"    {icon} Ch.{ch['chapter_number']} {ch.get('title', '')} [{ch['status']}]")
        print(f"  Status: {', '.join(f'{k}: {v}' for k, v in status_counts.items())}")

        active_threads = [t for t in threads if t['status'] == 'active']
        print(f"\n  Active Plot Threads ({len(active_threads)}):")
        for t in active_threads:
            print(f"    - {t['name']}")
        print()

# --- Planning --------------------------------------------------------------------

    def plan_novel(self, novel_id, extra_requirements=""):
        novel = repo.get_novel(self.conn, novel_id)
        if not novel:
            raise ValueError(f"Novel {novel_id} not found")

        # Calculate number of chapters from word count goal
        word_count_goal = novel.get("word_count_goal", 0) or 0
        if word_count_goal > 0:
            num_chapters = max(word_count_goal // 3000, 5)
        else:
            num_chapters = 20
        print(f"  AI planning {novel['title']} ({num_chapters} chapters based on {word_count_goal}-word goal)...")
        plan = self.planner.plan_novel(
            title=novel["title"],
            genre=novel.get("genre", ""),
            language=novel.get("language", "zh"),
            premise=novel.get("premise", ""),
            extra_requirements=extra_requirements,
            num_chapters=num_chapters,
        )

        for i, ch_data in enumerate(plan.get("characters", [])):
            rels = ch_data.get("relationships", {})
            repo.create_character(
                self.conn, novel_id,
                name=ch_data.get("name", f"Char{i}"),
                role=ch_data.get("role", ""),
                personality=ch_data.get("personality", ""),
                appearance=ch_data.get("appearance", ""),
                background=ch_data.get("background", ""),
                arc=ch_data.get("arc", ""),
                relationships=rels,
                first_appearance=0,
            )
        print(f"  Created {len(plan.get('characters', []))} characters")

        for pt_data in plan.get("plot_threads", []):
            repo.create_plot_thread(
                self.conn, novel_id,
                name=pt_data.get("name", ""),
                description=pt_data.get("description", ""),
                status=pt_data.get("status", "active"),
                related_chapters=pt_data.get("related_chapters", []),
            )
        print(f"  Created {len(plan.get('plot_threads', []))} plot threads")

        all_chapters = []
        for act in plan.get("structure", {}).get("acts", []):
            for ch_data in act.get("chapters", []):
                all_chapters.append(ch_data)

        for ch_data in all_chapters:
            ch_number = ch_data.get("number", 0)
            repo.create_chapter(
                self.conn, novel_id,
                chapter_number=ch_number,
                title=ch_data.get("title", ""),
                outline=ch_data.get("outline", ""),
                pov=ch_data.get("pov", ""),
                characters=ch_data.get("characters", []),
            )
        print(f"  Created {len(all_chapters)} chapters")

        world = plan.get("world_setting", {})
        if world:
            for key, val in world.items():
                if val:
                    repo.save_global_memory(
                        self.conn, novel_id,
                        f"world_{key}", str(val)
                    )
        print(f"  Saved world setting")
        return plan


    # --- Edit Operations ----------------------------------------------------------------

    def edit_novel(self, novel_id, **kwargs):
        """Update novel metadata."""
        repo.update_novel(self.conn, novel_id, **kwargs)
        self.conn.commit()
        print(f"  Novel {novel_id} updated")

    def edit_character(self, novel_id, character_name, **kwargs):
        """Update a character fields (role, personality, background, arc, etc)."""
        chars = repo.get_characters_by_names(self.conn, novel_id, [character_name])
        if not chars:
            raise ValueError(f"Character '{character_name}' not found in novel {novel_id}")
        repo.update_character(self.conn, chars[0]["id"], **kwargs)
        self.conn.commit()
        print(f"  Character '{character_name}' updated")

    def edit_plot_thread(self, novel_id, thread_name, **kwargs):
        """Update a plot thread fields (description, status, notes, etc)."""
        threads = repo.get_novel_plot_threads(self.conn, novel_id)
        matching = [t for t in threads if t["name"] == thread_name]
        if not matching:
            raise ValueError(f"Plot thread '{thread_name}' not found in novel {novel_id}")
        repo.update_plot_thread(self.conn, matching[0]["id"], **kwargs)
        self.conn.commit()
        print(f"  Plot thread '{thread_name}' updated")

    def edit_chapter(self, novel_id, chapter_number, **kwargs):
        """Update a chapter fields (title, outline, pov, plot_threads, etc)."""
        chapter = repo.get_chapter_by_number(self.conn, novel_id, chapter_number)
        if not chapter:
            raise ValueError(f"Chapter {chapter_number} not found in novel {novel_id}")
        repo.update_chapter(self.conn, chapter["id"], **kwargs)
        self.conn.commit()
        print(f"  Chapter {chapter_number} updated")

# --- Chapter Writing Pipeline ---------------------------------------------------

    def write_chapter(self, novel_id: int, chapter_number: int) -> str:
        novel = repo.get_novel(self.conn, novel_id)
        chapter = repo.get_chapter_by_number(self.conn, novel_id, chapter_number)
        if not novel or not chapter:
            raise ValueError(f"Novel {novel_id} or chapter {chapter_number} not found")

        repo.update_chapter(self.conn, chapter["id"], status="writing")

        char_names = chapter.get("characters", [])
        characters = repo.get_characters_by_names(self.conn, novel_id, char_names)

        prev_summaries = repo.get_chapter_summaries(self.conn, novel_id, limit=3)

        all_threads = repo.get_novel_plot_threads(self.conn, novel_id, status="active")
        chapter_thread_names = chapter.get("plot_threads", [])
        relevant_threads = [t for t in all_threads
                            if t["name"] in chapter_thread_names or not chapter_thread_names]

        style_guide = novel.get("style_guide", "") or "Standard narrative style"

        pending_records = repo.get_global_memory(
            self.conn, novel_id, "pending_items", limit=1
        )
        pending_items = []
        if pending_records:
            try:
                pending_items = json.loads(pending_records[0]["content"])
            except (json.JSONDecodeError, KeyError):
                pass

        context = ctx_builder.build_writer_context(
            novel, chapter, characters, prev_summaries,
            relevant_threads, style_guide, pending_items
        )

        print(f"  AI writing chapter {chapter_number}: {chapter.get('title', '')}...")
        print(f"    (context: {len(characters)} chars, {len(prev_summaries)} summaries, "
              f"{len(relevant_threads)} plot threads)")

        content = self.writer.write_chapter(context)
        word_count = len(content)

        repo.save_chapter_content(self.conn, chapter["id"], content)
        repo.update_chapter(self.conn, chapter["id"],
                            status="written", word_count=word_count)
        print(f"  Ch.{chapter_number} written: {word_count} chars")
        return content

    def review_chapter(self, novel_id: int, chapter_number: int) -> dict:
        novel = repo.get_novel(self.conn, novel_id)
        chapter = repo.get_chapter_by_number(self.conn, novel_id, chapter_number)
        if not novel or not chapter:
            raise ValueError(f"Novel {novel_id} or chapter {chapter_number} not found")

        content = repo.get_chapter_content(self.conn, chapter["id"])
        if not content:
            raise ValueError(f"Chapter {chapter_number} has no content yet")

        repo.update_chapter(self.conn, chapter["id"], status="reviewing")

        char_names = chapter.get("characters", [])
        characters = repo.get_characters_by_names(self.conn, novel_id, char_names)
        prev_summaries = repo.get_chapter_summaries(self.conn, novel_id, limit=3)
        style_guide = novel.get("style_guide", "") or "Standard narrative style"

        context = ctx_builder.build_reviewer_context(
            novel, chapter, characters, content,
            prev_summaries, style_guide
        )

        print(f"  AI reviewing chapter {chapter_number}...")
        review = self.reviewer.review_chapter(context)

        repo.save_review(
            self.conn, chapter["id"], content["version"],
            consistency_issues=review.get("consistency_issues", []),
            character_voice_issues=review.get("character_voice_issues", []),
            plot_holes=review.get("plot_holes", []),
            suggestions=review.get("suggestions", []),
            overall_score=review.get("overall_score", 0),
            assessment=review.get("assessment", ""),
        )

        score = review.get("overall_score", 0)
        issues_count = (
            len(review.get("consistency_issues", []))
            + len(review.get("character_voice_issues", []))
            + len(review.get("plot_holes", []))
        )
        print(f"  Review score: {score}/100 with {issues_count} issues")
        return review

    def revise_chapter(self, novel_id: int, chapter_number: int) -> str:
        novel = repo.get_novel(self.conn, novel_id)
        chapter = repo.get_chapter_by_number(self.conn, novel_id, chapter_number)
        if not novel or not chapter:
            raise ValueError(f"Novel {novel_id} or chapter {chapter_number} not found")

        content = repo.get_chapter_content(self.conn, chapter["id"])
        review = repo.get_review(self.conn, chapter["id"])
        if not content or not review:
            raise ValueError(f"No content or review for chapter {chapter_number}")

        char_names = chapter.get("characters", [])
        characters = repo.get_characters_by_names(self.conn, novel_id, char_names)
        style_guide = novel.get("style_guide", "") or "Standard narrative style"

        context = ctx_builder.build_reviser_context(
            novel, chapter, characters, content, review, style_guide
        )

        print(f"  AI revising chapter {chapter_number} based on review...")

        reviser = BaseAgent(
            self.client, self.model,
            system_prompt=REVISER_SYSTEM,
            temperature=0.7,
        )
        user_msg = REVISER_USER_TEMPLATE.format(**context)
        revised_content = reviser.call(user_msg)

        new_version = (content["version"] or 1) + 1
        word_count = len(revised_content)

        repo.save_chapter_content(
            self.conn, chapter["id"], revised_content, version=new_version
        )
        repo.update_chapter(self.conn, chapter["id"],
                            status="written", word_count=word_count)
        print(f"  Revised v{new_version}: {word_count} chars")
        return revised_content

    def update_memory(self, novel_id: int, chapter_number: int):
        novel = repo.get_novel(self.conn, novel_id)
        chapter = repo.get_chapter_by_number(self.conn, novel_id, chapter_number)
        if not novel or not chapter:
            raise ValueError(f"Novel {novel_id} or chapter {chapter_number} not found")

        content = repo.get_chapter_content(self.conn, chapter["id"])
        if not content:
            raise ValueError(f"Chapter {chapter_number} has no content")

        char_names = chapter.get("characters", [])
        characters = repo.get_characters_by_names(self.conn, novel_id, char_names)

        context = ctx_builder.build_memory_context(
            novel, chapter, characters, content
        )

        print(f"  AI updating memory from chapter {chapter_number}...")
        memory = self.memory.update_memory(context)

        repo.save_chapter_content(
            self.conn, chapter["id"],
            content["content"],
            version=content["version"],
            summary=memory.get("summary", ""),
            key_events=memory.get("key_events", []),
        )

        for cd in memory.get("character_developments", []):
            char_name = cd.get("character_name", "")
            matching = repo.get_characters_by_names(self.conn, novel_id, [char_name])
            if matching:
                existing = matching[0]
                arc_update = cd.get("arc_update", "")
                if arc_update and existing["arc"]:
                    new_arc = existing["arc"] + " | " + arc_update
                elif arc_update:
                    new_arc = arc_update
                else:
                    new_arc = existing["arc"]
                repo.update_character(self.conn, existing["id"], arc=new_arc)

        for tp in memory.get("plot_thread_progress", []):
            thread_name = tp.get("thread_name", "")
            status_update = tp.get("status_update", "")
            all_threads = repo.get_novel_plot_threads(self.conn, novel_id)
            matching = [t for t in all_threads if t["name"] == thread_name]
            if matching and status_update:
                repo.update_plot_thread(self.conn, matching[0]["id"],
                                         status=status_update)

        for wu in memory.get("world_updates", []):
            repo.create_world_entry(
                self.conn, novel_id,
                category=wu.get("category", "general"),
                name=wu.get("name", ""),
                description=wu.get("description", ""),
            )

        pending = memory.get("pending_items", [])
        if pending:
            repo.save_global_memory(
                self.conn, novel_id,
                "pending_items", json.dumps(pending, ensure_ascii=False)
            )

        repo.update_chapter(self.conn, chapter["id"], status="finalized")
        print(f"  Memory updated")
        return memory


    def _rewrite_word_count(self, novel_id, chapter_number, target_wc=3000):
        """Rewrite a chapter to meet the target word count range (code-level check)."""
        from ..agents.base import BaseAgent
        novel = repo.get_novel(self.conn, novel_id)
        chapter = repo.get_chapter_by_number(self.conn, novel_id, chapter_number)
        content_rec = repo.get_chapter_content(self.conn, chapter["id"])
        if not content_rec:
            raise ValueError(f"Chapter {chapter_number} has no content to rewrite")

        char_names = chapter.get("characters", [])
        characters = repo.get_characters_by_names(self.conn, novel_id, char_names)
        chars_section = "; ".join(f"{c['name']} ({c.get('role','')})" for c in characters) if characters else "None"

        prompt = f"""Rewrite Chapter {chapter_number}: {chapter.get("title", "")}

Current word count: {len(content_rec["content"])}
Target: approximately {target_wc} words (between 2500 and 3500).

## Outline
{chapter.get("outline", "")}

## POV
{chapter.get("pov", "")}

## Characters
{chars_section}

## Original Opening (first 300 chars)
{content_rec["content"][:300]}

Rewrite this chapter to reach approximately {target_wc} words. Keep the same outline, POV, and character consistency. Expand or condense the content as needed. Output the full revised chapter."""

        agent = BaseAgent(
            self.client, self.model,
            system_prompt="You are a professional novelist. Revise chapters to meet word count targets while preserving story quality.",
            temperature=0.7,
        )
        revised = agent.call(prompt)

        new_version = (content_rec["version"] or 1) + 1
        repo.save_chapter_content(self.conn, chapter["id"], revised, version=new_version)
        repo.update_chapter(self.conn, chapter["id"], status="written", word_count=len(revised))
        print(f"    Rewritten (v{new_version}): {len(revised)} chars")
        return revised

    # --- Full Pipeline ----------------------------------------------------------------

    def run_chapter_pipeline(self, novel_id: int, chapter_number: int,
                              auto_revise: bool = True):
        print(f"\n{'='*50}")
        print(f"  Processing Chapter {chapter_number}")
        print(f"{'='*50}")

        # === Write chapter ===
        content = self.write_chapter(novel_id, chapter_number)

        # === Pre-review word count check (code-level) ===
        wc = len(content)
        wc_attempts = 0
        while (wc < 2500 or wc > 3500) and wc_attempts < 3:
            wc_attempts += 1
            print(f"  [WC] Word count {wc} outside target [2500, 3500], re-writing (attempt {wc_attempts}/3)...")
            content = self._rewrite_word_count(novel_id, chapter_number, target_wc=3000)
            wc = len(content)

        if wc_attempts > 0:
            if 2500 <= wc <= 3500:
                print(f"  [WC] Word count {wc} OK after rewrite.")
            else:
                print(f"  [WC] Warning: word count {wc} still outside target after {wc_attempts} rewrite(s).")

        review = self.review_chapter(novel_id, chapter_number)

        if auto_revise:
            score = review.get("overall_score", 100)
            revision_round = 0
            while score < _REVISION_THRESHOLD and revision_round < _MAX_REVISIONS:
                revision_round += 1
                print(f"  Score {score} below {_REVISION_THRESHOLD}, revising (round {revision_round})")
                self.revise_chapter(novel_id, chapter_number)
                review = self.review_chapter(novel_id, chapter_number)
                score = review.get("overall_score", 100)

            if score >= _REVISION_THRESHOLD:
                print(f"  Final score {score}, passed")
            else:
                print(f"  Max revisions reached, final score {score}")

        self.update_memory(novel_id, chapter_number)

        print(f"{'='*50}")
        print(f"  Chapter {chapter_number} complete")
        print(f"{'='*50}")

    def run_full_pipeline(self, novel_id: int,
                           start_chapter: int = 1,
                           end_chapter: int | None = None,
                           auto_revise: bool = True):
        chapters = repo.get_novel_chapters(self.conn, novel_id)
        if not chapters:
            raise ValueError(f"Novel {novel_id} has no chapters. Run plan_novel first.")

        if end_chapter is None:
            end_chapter = max(c["chapter_number"] for c in chapters)

        for ch in chapters:
            if ch["chapter_number"] < start_chapter:
                continue
            if ch["chapter_number"] > end_chapter:
                break
            if ch["status"] == "finalized":
                print(f"  Ch.{ch['chapter_number']} already finalized, skipping")
                continue
            self.run_chapter_pipeline(novel_id, ch["chapter_number"], auto_revise)

        print(f"\n{'='*50}")
        print(f"  All chapters processed")
        print(f"{'='*50}")

# --- Final Consistency Check ----------------------------------------------------

    def final_consistency_check(self, novel_id: int):
        novel = repo.get_novel(self.conn, novel_id)
        if not novel:
            raise ValueError(f"Novel {novel_id} not found")

        characters = repo.get_novel_characters(self.conn, novel_id)
        chapter_summaries = repo.get_chapter_summaries(self.conn, novel_id, limit=999)
        plot_threads = repo.get_novel_plot_threads(self.conn, novel_id)

        context = ctx_builder.build_consistency_context(
            novel, characters, chapter_summaries, plot_threads
        )

        print(f"  AI running consistency check...")

        checker = BaseAgent(
            self.client, self.model,
            system_prompt=CONSISTENCY_SYSTEM,
            temperature=0.3,
        )
        user_msg = CONSISTENCY_USER_TEMPLATE.format(**context)
        result = checker.call_json(user_msg)

        print(f"\n{'='*60}")
        print(f"  Consistency Report")
        print(f"{'='*60}")
        print(f"  Assessment: {result.get('overall_assessment', '')}")
        print()

        for field, label in [
            ("continuity_issues", "Continuity Issues"),
            ("character_arc_issues", "Character Arc Issues"),
            ("unresolved_threads", "Unresolved Threads"),
            ("timeline_issues", "Timeline Issues"),
        ]:
            items = result.get(field, [])
            if items:
                print(f"  {label}:")
                for item in items:
                    print(f"    - {item}")
                print()

        if result.get("suggestions", []):
            print(f"  Suggestions:")
            for s in result["suggestions"]:
                print(f"    - {s}")
            print()

        print(f"{'='*60}")
        return result

    def close(self):
        self.conn.close()
