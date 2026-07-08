"""Context builder - minimal context for each agent."""

import json


def build_writer_context(novel, chapter, characters, prev_summaries,
                         plot_threads, style_guide, pending_items):
    chars_section = _format_characters(characters)
    if prev_summaries:
        summaries_text = chr(10).join(
            f"Ch {s['chapter_number']} - {s['title']}: {s['summary']}"
            for s in prev_summaries
        )
    else:
        summaries_text = ""

    pts_text = chr(10).join(
        f"- {pt['name']} ({pt['description']}) [status: {pt['status']}]"
        for pt in plot_threads
    ) if plot_threads else ""

    pending_text = chr(10).join(f"- {item}" for item in pending_items) if pending_items else "None"

    return {
        "chapter_number": chapter["chapter_number"],
        "chapter_title": chapter.get("title", ""),
        "chapter_outline": chapter.get("outline", ""),
        "characters_section": chars_section,
        "pov": chapter.get("pov", ""),
        "previous_summaries": summaries_text,
        "plot_threads_section": pts_text,
        "style_guide": style_guide,
        "pending_items": pending_text,
    }


def build_reviewer_context(novel, chapter, characters, content,
                            prev_summaries, style_guide):
    chars_section = _format_characters(characters)
    summaries_text = chr(10).join(
        f"Ch {s['chapter_number']} - {s['title']}: {s['summary']}"
        for s in prev_summaries
    ) if prev_summaries else ""
    return {
        "novel_title": novel["title"],
        "chapter_number": chapter["chapter_number"],
        "chapter_title": chapter.get("title", ""),
        "chapter_outline": chapter.get("outline", ""),
        "characters_section": chars_section,
        "previous_summaries": summaries_text,
        "style_guide": style_guide,
        "chapter_content": content["content"],
    }


def build_memory_context(novel, chapter, characters, content):
    chars_section = _format_characters(characters)
    return {
        "novel_title": novel["title"],
        "chapter_number": chapter["chapter_number"],
        "chapter_title": chapter.get("title", ""),
        "chapter_outline": chapter.get("outline", ""),
        "characters_section": chars_section,
        "chapter_content": content["content"],
    }


def build_reviser_context(novel, chapter, characters, content, review, style_guide):
    chars_section = _format_characters(characters)
    issues_text = chr(10).join(f"- {issue}" for issue in review.get("consistency_issues", []))
    cv_text = chr(10).join(f"- {issue}" for issue in review.get("character_voice_issues", []))
    holes_text = chr(10).join(f"- {h}" for h in review.get("plot_holes", []))
    sugg_text = chr(10).join(f"- {s}" for s in review.get("suggestions", []))
    return {
        "chapter_number": chapter["chapter_number"],
        "chapter_title": chapter.get("title", ""),
        "original_content": content["content"],
        "review_assessment": review.get("assessment", ""),
        "consistency_issues": issues_text or "None",
        "character_voice_issues": cv_text or "None",
        "plot_holes": holes_text or "None",
        "suggestions": sugg_text or "None",
        "chapter_outline": chapter.get("outline", ""),
        "characters_section": chars_section,
    }


def build_consistency_context(novel, characters, chapter_summaries, plot_threads):
    chars_overview = chr(10)*2 + ((chr(10)*2)).join(
        f"[{c['name']}] ({c['role']})\n"
        f"Personality: {c['personality']}\n"
        f"Background: {c['background']}\n"
        f"Arc: {c['arc']}\n"
        f"Relationships: {json.dumps(c.get('relationships', {}), ensure_ascii=False)}"
        for c in characters
    )
    summaries_text = chr(10).join(
        f"Ch {s['chapter_number']} - {s['title']}: {s['summary']}"
        for s in chapter_summaries
    )
    threads_text = chr(10).join(
        f"- {pt['name']}: {pt['description']} [status: {pt['status']}]"
        for pt in plot_threads
    )
    return {
        "novel_title": novel["title"],
        "characters_overview": chars_overview,
        "chapter_summaries": summaries_text,
        "plot_threads": threads_text,
    }


def _format_characters(characters):
    parts = []
    for c in characters:
        rels = c.get("relationships", {})
        rels_text = "; ".join(f"{k}: {v}" for k, v in rels.items()) if rels else ""
        parts.append(
            f"[{c['name']}] ({c.get('role', '')})\n"
            f"Personality: {c.get('personality', '')}\n"
            f"Appearance: {c.get('appearance', '')}\n"
            f"Background: {c.get('background', '')}\n"
            f"Arc: {c.get('arc', '')}\n"
            f"Relationships: {rels_text}"
        )
    return "\n---\n".join(parts)
