"""novel-writer: AI multi-agent novel writing tool.

Usage:
  python -m novel_writer configure       Set API key and model
  python -m novel_writer create          Create a new novel
  python -m novel_writer list            List all novels
  python -m novel_writer plan <id>       Generate outline with AI
  python -m novel_writer status <id>     Show novel progress
  python -m novel_writer write <id> [ch] Write a chapter
  python -m novel_writer review <id> <ch> Review a chapter
  python -m novel_writer pipeline <id> [s] [e]  Run full pipeline
  python -m novel_writer pipeline:1 <id> <ch> Run pipeline for one chapter
  python -m novel_writer consistency <id> Final consistency check
  python -m novel_writer edit novel <id>  Edit novel info
  python -m novel_writer edit char <id> <name>  Edit character
  python -m novel_writer edit thread <id> <name>  Edit plot thread
  python -m novel_writer edit ch <id> <num>  Edit chapter
  python -m novel_writer export <id>     Export novel to Markdown
  python -m novel_writer interactive     Interactive mode
"""

import os
import sys

from .config import load_config, save_config
from .workflow.orchestrator import Orchestrator
from .db import repository as repo
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table


console = Console()


def cmd_configure():
    config = load_config()
    console.print(Panel("Configure DeepSeek API", style="bold blue"))
    api_key = Prompt.ask("API Key", default=config.get("api_key", ""), password=True)
    api_base = Prompt.ask("Base URL", default=config.get("api_base", "https://api.deepseek.com/v1"))
    model = Prompt.ask("Model", default=config.get("model", "deepseek-chat"))
    config["api_key"] = api_key
    config["api_base"] = api_base
    config["model"] = model
    save_config(config)
    console.print("[green]Saved config to ~/.novel_writer_config.json[/green]")


def cmd_create():
    config = load_config()
    if not config.get("api_key"):
        console.print("[red]Please run configure first to set API Key[/red]")
        return
    orchestrator = Orchestrator(config)
    console.print(Panel("Create New Novel", style="bold green"))
    title = Prompt.ask("Title")
    genre = Prompt.ask("Genre (fantasy/sci-fi/romance)", default="")
    language = Prompt.ask("Language", default="zh")
    premise = Prompt.ask("Premise/Logline", default="")
    style_guide = Prompt.ask("Style Guide (optional)", default="")
    console.print("\n[dim]Additional options (optional)[/dim]")
    target_audience = Prompt.ask("Target Audience", default="")
    wc_str = Prompt.ask("Word Count Goal", default="0")
    word_count_goal = int(wc_str) if wc_str.isdigit() else 0
    novel_id = orchestrator.create_novel(
        title=title, genre=genre, language=language, premise=premise,
        style_guide=style_guide, target_audience=target_audience,
        word_count_goal=word_count_goal,
    )
    if Confirm.ask("Generate outline with AI now?"):
        extra = Prompt.ask("Extra requirements", default="")
        orchestrator.plan_novel(novel_id, extra_requirements=extra)
    orchestrator.close()


def cmd_list():
    config = load_config()
    orchestrator = Orchestrator(config)
    novels = orchestrator.list_novels()
    if not novels:
        console.print("[yellow]No novels found[/yellow]")
        orchestrator.close()
        return
    table = Table(title="Novels")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="bold")
    table.add_column("Genre", style="green")
    table.add_column("Lang")
    table.add_column("Created")
    for n in novels:
        table.add_row(str(n["id"]), n["title"], n.get("genre", ""), n.get("language", "zh"), n.get("created_at", ""))
    console.print(table)
    orchestrator.close()


def cmd_plan(novel_id_str):
    novel_id = int(novel_id_str)
    config = load_config()
    orchestrator = Orchestrator(config)
    novel = orchestrator.get_novel(novel_id)
    if not novel:
        console.print("[red]Novel not found[/red]")
        orchestrator.close()
        return
    extra = Prompt.ask("Extra requirements", default="")
    orchestrator.plan_novel(novel_id, extra_requirements=extra)
    orchestrator.close()


def cmd_status(novel_id_str):
    novel_id = int(novel_id_str)
    config = load_config()
    orchestrator = Orchestrator(config)
    orchestrator.show_novel_status(novel_id)
    orchestrator.close()


def cmd_write(novel_id_str, chapter_str=None):
    novel_id = int(novel_id_str)
    config = load_config()
    orchestrator = Orchestrator(config)
    if chapter_str:
        orchestrator.write_chapter(novel_id, int(chapter_str))
    else:
        row = orchestrator.conn.execute(
            "SELECT chapter_number FROM chapters WHERE novel_id=? AND status='outlined' ORDER BY chapter_number LIMIT 1",
            (novel_id,)
        ).fetchone()
        if row:
            orchestrator.write_chapter(novel_id, row["chapter_number"])
        else:
            console.print("[yellow]No chapters ready for writing[/yellow]")
    orchestrator.close()


def cmd_review(novel_id_str, chapter_str):
    novel_id = int(novel_id_str)
    chapter_number = int(chapter_str)
    config = load_config()
    orchestrator = Orchestrator(config)
    orchestrator.review_chapter(novel_id, chapter_number)
    orchestrator.close()


def cmd_pipeline(novel_id_str, start_str=None, end_str=None):
    novel_id = int(novel_id_str)
    config = load_config()
    orchestrator = Orchestrator(config)
    start = int(start_str) if start_str else 1
    end = int(end_str) if end_str else None
    auto_revise = Confirm.ask("Auto-revise on low score?", default=True)
    orchestrator.run_full_pipeline(novel_id, start, end, auto_revise=auto_revise)
    orchestrator.close()


def cmd_pipeline_one(novel_id_str, chapter_str):
    novel_id = int(novel_id_str)
    chapter_number = int(chapter_str)
    config = load_config()
    orchestrator = Orchestrator(config)
    auto_revise = Confirm.ask("Auto-revise on low score?", default=True)
    orchestrator.run_chapter_pipeline(novel_id, chapter_number, auto_revise=auto_revise)
    orchestrator.close()


def cmd_consistency(novel_id_str):
    novel_id = int(novel_id_str)
    config = load_config()
    orchestrator = Orchestrator(config)
    orchestrator.final_consistency_check(novel_id)
    orchestrator.close()


def cmd_interactive():
    config = load_config()
    if not config.get("api_key"):
        console.print("[red]Please run configure first to set API Key[/red]")
        return
    orchestrator = Orchestrator(config)
    console.print(Panel.fit(
        "[bold]AI Novel Writer Interactive[/bold]\n"
        "Type [cyan]help[/cyan] for commands or [cyan]exit[/cyan] to quit",
        style="bold blue"
    ))
    while True:
        try:
            cmd = Prompt.ask("[bold cyan]novel>[/bold cyan]")
        except (EOFError, KeyboardInterrupt):
            break
        cmd = cmd.strip()
        if not cmd:
            continue
        if cmd in ("exit", "quit", "q"):
            break
        if cmd == "help":
            console.print("""
[bold]Commands:[/bold]
  [cyan]create[/cyan]             Create new novel
  [cyan]list[/cyan]               List all novels
  [cyan]plan <id>[/cyan]          Plan outline
  [cyan]status <id>[/cyan]        Show progress
  [cyan]write <id> [ch][/cyan]    Write chapter
  [cyan]review <id> <ch>[/cyan]   Review chapter
  [cyan]pipe <id> [s] [e][/cyan]  Run full pipeline
  [cyan]pipe:1 <id> <ch>[/cyan]   Run one chapter pipe
  [cyan]check <id>[/cyan]         Consistency check
  [cyan]edit novel <id>[/cyan]    Edit novel info
  [cyan]edit char <id> <n>[/cyan] Edit character
  [cyan]edit thread <id> <n>[/cyan] Edit plot thread
  [cyan]edit ch <id> <n>[/cyan]   Edit chapter
  [cyan]export <id>[/cyan]        Export novel to Markdown
  [cyan]help[/cyan]               Show this help
  [cyan]exit[/cyan]               Exit
            """)
            continue
        parts = cmd.split()
        action = parts[0]
        try:
            if action == "create":
                title = Prompt.ask("Title")
                genre = Prompt.ask("Genre", default="")
                premise = Prompt.ask("Premise", default="")
                novel_id = orchestrator.create_novel(title, genre=genre, premise=premise)
                if Confirm.ask("Generate outline now?"):
                    extra = Prompt.ask("Extra req", default="")
                    orchestrator.plan_novel(novel_id, extra_requirements=extra)
            elif action == "list":
                novels = orchestrator.list_novels()
                if not novels:
                    console.print("[yellow]None[/yellow]")
                else:
                    for n in novels:
                        console.print(f"  [cyan]{n['id']}[/cyan]  {n['title']}  ({n.get('genre','')})")
            elif action == "plan" and len(parts) >= 2:
                orchestrator.plan_novel(int(parts[1]))
            elif action == "status" and len(parts) >= 2:
                orchestrator.show_novel_status(int(parts[1]))
            elif action == "write" and len(parts) >= 2:
                ch = int(parts[2]) if len(parts) >= 3 else None
                if ch:
                    orchestrator.write_chapter(int(parts[1]), ch)
                else:
                    row = orchestrator.conn.execute(
                        "SELECT chapter_number FROM chapters WHERE novel_id=? AND status='outlined' ORDER BY chapter_number LIMIT 1",
                        (int(parts[1]),)
                    ).fetchone()
                    if row:
                        orchestrator.write_chapter(int(parts[1]), row["chapter_number"])
                    else:
                        console.print("[yellow]No chapters ready for writing[/yellow]")
            elif action == "review" and len(parts) >= 3:
                orchestrator.review_chapter(int(parts[1]), int(parts[2]))
            elif action == "pipe" and len(parts) >= 2:
                s = int(parts[2]) if len(parts) >= 3 else 1
                e = int(parts[3]) if len(parts) >= 4 else None
                orchestrator.run_full_pipeline(int(parts[1]), s, e)
            elif action == "pipe:1" and len(parts) >= 3:
                orchestrator.run_chapter_pipeline(int(parts[1]), int(parts[2]))
            elif action == "check" and len(parts) >= 2:
                orchestrator.final_consistency_check(int(parts[1]))
            elif action == "export" and len(parts) >= 2:
                cmd_export(parts[1])
            elif action == "edit":
                if len(parts) < 3:
                    console.print("[red]Usage: edit novel|char|thread|ch <id> [name] ...[/red]")
                    continue
                sub = parts[1]
                target_id = int(parts[2])
                try:
                    if sub == "novel":
                        fields = Prompt.ask("Fields (comma-sep, e.g. title,genre,premise)", default="")
                        kwargs = {}
                        for f in fields.split(","):
                            f = f.strip()
                            if f:
                                kwargs[f] = Prompt.ask(f"  {f}", default="")
                        orchestrator.edit_novel(target_id, **kwargs)
                    elif sub == "char" and len(parts) >= 4:
                        char_name = parts[3]
                        fields = Prompt.ask("Fields (e.g. role,personality,background,arc)", default="")
                        kwargs = {}
                        for f in fields.split(","):
                            f = f.strip()
                            if f:
                                kwargs[f] = Prompt.ask(f"  {f}", default="")
                        orchestrator.edit_character(target_id, char_name, **kwargs)
                    elif sub == "thread" and len(parts) >= 4:
                        tname = parts[3]
                        fields = Prompt.ask("Fields (e.g. description,status,notes)", default="")
                        kwargs = {}
                        for f in fields.split(","):
                            f = f.strip()
                            if f:
                                kwargs[f] = Prompt.ask(f"  {f}", default="")
                        orchestrator.edit_plot_thread(target_id, tname, **kwargs)
                    elif sub == "ch" and len(parts) >= 4:
                        ch_num = int(parts[3])
                        fields = Prompt.ask("Fields (e.g. title,outline,pov)", default="")
                        kwargs = {}
                        for f in fields.split(","):
                            f = f.strip()
                            if f:
                                kwargs[f] = Prompt.ask(f"  {f}", default="")
                        orchestrator.edit_chapter(target_id, ch_num, **kwargs)
                    else:
                        console.print("[red]Usage: edit novel|char|thread|ch <id> [name] ...[/red]")
                except Exception as e:
                    console.print(f"[red]Error: {e}[/red]")
            else:
                console.print(f"[red]Unknown command: {cmd}[/red]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
    orchestrator.close()
    console.print("[green]Bye[/green]")



def cmd_edit(args):
    """Edit novel/character/thread/chapter from CLI."""
    if len(args) < 2:
        console.print("[red]Usage: edit novel|char|thread|ch <id> [name] <field=value> ...[/red]")
        return
    config = load_config()
    orchestrator = Orchestrator(config)
    sub = args[0]
    try:
        if sub == "novel":
            novel_id = int(args[1])
            kwargs = {}
            for pair in args[2:]:
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    kwargs[k] = v
            if not kwargs:
                novel = orchestrator.get_novel(novel_id)
                if not novel:
                    console.print(f"[red]Novel {novel_id} not found[/red]")
                    orchestrator.close()
                    return
                console.print(Panel(f"Editing Novel: {novel['title']}", style="bold yellow"))
                for key in ["title", "genre", "language", "premise", "style_guide", "target_audience"]:
                    val = Prompt.ask(f"  {key}", default=novel.get(key, ""))
                    if val != novel.get(key, ""):
                        kwargs[key] = val
                wc_str = Prompt.ask("  word_count_goal", default=str(novel.get("word_count_goal", 0)))
                if wc_str.isdigit():
                    wc = int(wc_str)
                    if wc != novel.get("word_count_goal", 0):
                        kwargs["word_count_goal"] = wc
            orchestrator.edit_novel(novel_id, **kwargs)
        elif sub == "char" and len(args) >= 3:
            novel_id = int(args[1])
            char_name = args[2]
            kwargs = {}
            for pair in args[3:]:
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    kwargs[k] = v
            if not kwargs:
                from .db import repository as repo
                matching = repo.get_characters_by_names(orchestrator.conn, novel_id, [char_name])
                if not matching:
                    console.print(f"[red]Character '{char_name}' not found[/red]")
                    orchestrator.close()
                    return
                c = matching[0]
                console.print(Panel(f"Editing Character: {c['name']}", style="bold yellow"))
                for key in ["role", "personality", "appearance", "background", "arc"]:
                    val = Prompt.ask(f"  {key}", default=c.get(key, ""))
                    if val != c.get(key, ""):
                        kwargs[key] = val
            orchestrator.edit_character(novel_id, char_name, **kwargs)
        elif sub == "thread" and len(args) >= 3:
            novel_id = int(args[1])
            thread_name = args[2]
            kwargs = {}
            for pair in args[3:]:
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    kwargs[k] = v
            if not kwargs:
                from .db import repository as repo
                all_t = repo.get_novel_plot_threads(orchestrator.conn, novel_id)
                matching = [t for t in all_t if t["name"] == thread_name]
                if not matching:
                    console.print(f"[red]Thread '{thread_name}' not found[/red]")
                    orchestrator.close()
                    return
                t = matching[0]
                console.print(Panel(f"Editing Plot Thread: {t['name']}", style="bold yellow"))
                for key in ["description", "status", "notes"]:
                    val = Prompt.ask(f"  {key}", default=t.get(key, ""))
                    if val != t.get(key, ""):
                        kwargs[key] = val
            orchestrator.edit_plot_thread(novel_id, thread_name, **kwargs)
        elif sub == "ch" and len(args) >= 3:
            novel_id = int(args[1])
            ch_num = int(args[2])
            kwargs = {}
            for pair in args[3:]:
                if "=" in pair:
                    k, v = pair.split("=", 1)
                    kwargs[k] = v
            if not kwargs:
                from .db import repository as repo
                ch = repo.get_chapter_by_number(orchestrator.conn, novel_id, ch_num)
                if not ch:
                    console.print(f"[red]Chapter {ch_num} not found[/red]")
                    orchestrator.close()
                    return
                console.print(Panel(f"Editing Chapter {ch_num}: {ch.get('title','')}", style="bold yellow"))
                for key in ["title", "outline", "pov"]:
                    val = Prompt.ask(f"  {key}", default=ch.get(key, ""))
                    if val != ch.get(key, ""):
                        kwargs[key] = val
            orchestrator.edit_chapter(novel_id, ch_num, **kwargs)
        else:
            console.print("[red]Usage: edit novel|char|thread|ch <id> [name] ...[/red]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
    finally:
        orchestrator.close()



def cmd_export(novel_id_str):
    novel_id = int(novel_id_str)
    config = load_config()
    orchestrator = Orchestrator(config)
    conn = orchestrator.conn

    novel = repo.get_novel(conn, novel_id)
    if not novel:
        console.print("[red]Novel not found[/red]")
        orchestrator.close()
        return

    chapters = repo.get_novel_chapters(conn, novel_id)
    characters = repo.get_novel_characters(conn, novel_id)

    md = []
    md.append(f"# {novel['title']}")
    md.append("")
    if novel.get("premise"):
        md.append(f"> {novel['premise']}")
        md.append("")
    md.append(f"- **Genre:** {novel.get('genre', 'N/A')}")
    md.append(f"- **Language:** {novel.get('language', 'zh')}")
    md.append(f"- **Style:** {novel.get('style_guide', 'Standard')}")
    md.append(f"- **Target Audience:** {novel.get('target_audience', 'N/A')}")
    md.append(f"- **Created:** {novel.get('created_at', '')}")
    md.append("")
    md.append("---")
    md.append("")

    if characters:
        md.append("## Characters")
        md.append("")
        for c in characters:
            md.append(f"### {c['name']} ({c.get('role', 'Unknown')})")
            if c.get("personality"):
                md.append(f"- **Personality:** {c['personality']}")
            if c.get("appearance"):
                md.append(f"- **Appearance:** {c['appearance']}")
            if c.get("background"):
                md.append(f"- **Background:** {c['background']}")
            if c.get("arc"):
                md.append(f"- **Arc:** {c['arc']}")
            md.append("")

    written_count = 0
    for ch in chapters:
        content_rec = repo.get_chapter_content(conn, ch["id"])
        chapter_title = ch.get("title", "") or f"Chapter {ch['chapter_number']}"

        md.append(f"## Chapter {ch['chapter_number']}: {chapter_title}")
        if ch.get("pov"):
            md.append(f"*POV: {ch['pov']}*")
        if ch.get("outline"):
            md.append("")
            md.append(f"*Outline: {ch['outline']}*")
        md.append("")

        if content_rec and content_rec.get("content", "").strip():
            md.append(content_rec["content"].strip())
            written_count += 1
        else:
            md.append("*[Content not yet written]*")
        md.append("")
        md.append("---")
        md.append("")

    novels_dir = config.get("novels_dir", "./novels")
    os.makedirs(novels_dir, exist_ok=True)
    safe_title = novel["title"].replace(" ", "_").replace("/", "-").replace("\\", "-")[:64]
    filepath = os.path.join(novels_dir, f"{safe_title}.md")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(md))

    total_ch = len(chapters)
    console.print(f"\n[green]Exported [bold]{novel['title']}[/bold] to [cyan]{filepath}[/cyan][/green]")
    console.print(f"  Chapters: {written_count}/{total_ch} written, {total_ch - written_count} pending")
    orchestrator.close()

def main():
    if len(sys.argv) < 2:
        console.print(__doc__.strip())
        return
    command = sys.argv[1]
    args = sys.argv[2:]
    commands = {
        "configure": lambda: cmd_configure(),
        "create": lambda: cmd_create(),
        "list": lambda: cmd_list(),
        "plan": lambda: cmd_plan(args[0]) if args else console.print("[red]Missing novel ID[/red]"),
        "status": lambda: cmd_status(args[0]) if args else console.print("[red]Missing novel ID[/red]"),
        "write": lambda: cmd_write(args[0], args[1] if len(args) > 1 else None) if args else console.print("[red]Missing novel ID[/red]"),
        "review": lambda: cmd_review(args[0], args[1]) if len(args) >= 2 else console.print("[red]Missing novel ID or chapter[/red]"),
        "pipeline": lambda: cmd_pipeline(args[0], args[1] if len(args) > 1 else None, args[2] if len(args) > 2 else None) if args else console.print("[red]Missing novel ID[/red]"),
        "pipeline:1": lambda: cmd_pipeline_one(args[0], args[1]) if len(args) >= 2 else console.print("[red]Missing novel ID or chapter[/red]"),
        "consistency": lambda: cmd_consistency(args[0]) if args else console.print("[red]Missing novel ID[/red]"),
        "edit": lambda: cmd_edit(args) if len(args) >= 2 else console.print("[red]Usage: edit novel|char|thread|ch ...[/red]"),
        "export": lambda: cmd_export(args[0]) if args else console.print("[red]Missing novel ID[/red]"),
        "interactive": lambda: cmd_interactive(),
    }
    handler = commands.get(command)
    if handler:
        handler()
    else:
        console.print(f"[red]Unknown: {command}[/red]")
        console.print(__doc__.strip())


if __name__ == "__main__":
    main()