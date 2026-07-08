# novel-writer

AI-powered multi-agent novel writing tool. Uses a team of specialized AI agents (Planner, Writer, Reviewer, Memory) to plan, write, review, and revise novels chapter by chapter.

## Features

- **Multi-agent pipeline**: Planner, Writer, Reviewer, and Memory agents collaborate autonomously
- **Chapter-by-chapter writing**: Each chapter written with minimal context to maintain quality and handle long-form narratives
- **Review & Revision loop**: Chapters are automatically reviewed and revised until they meet quality thresholds
- **Automatic consistency check**: Final pass checks for plot holes, character arc issues, and unresolved threads
- **Word count enforcement**: Configurable target word count determines chapter count; pre-review word count check (2500-3500 target) triggers auto-rewrites
- **Interactive mode**: Run the full pipeline or individual steps via a CLI prompt
- **Edit commands**: Modify novel info, characters, plot threads, and chapters without restarting
- **Memory management**: Key events, character development, and plot thread progress tracked per chapter
- **SQLite storage**: All novels, chapters, characters, and review data stored locally

## Requirements

- Python 3.10+
- OpenAI-compatible API (tested with DeepSeek, works with any OpenAI-compatible provider)

## Quick Start

```
pip install openai rich
```

```
python -m novel_writer configure
```

You will be prompted for:
- API Key
- Base URL (defaults to https://api.deepseek.com/v1)
- Model name (defaults to deepseek-chat)

Configuration is saved to ~/.novel_writer_config.json.

## Usage

### CLI Commands

| Command | Description |
|---|---|
| python -m novel_writer configure | Set API key and model |
| python -m novel_writer create | Create a new novel |
| python -m novel_writer list | List all novels |
| python -m novel_writer plan <id> | Generate outline with AI |
| python -m novel_writer status <id> | Show novel progress |
| python -m novel_writer write <id> [ch] | Write a chapter |
| python -m novel_writer review <id> <ch> | Review a chapter |
| python -m novel_writer pipeline <id> [s] [e] | Run full pipeline |
| python -m novel_writer pipeline:1 <id> <ch> | Run pipeline for one chapter |
| python -m novel_writer consistency <id> | Final consistency check |
| python -m novel_writer edit novel <id> | Edit novel info |
| python -m novel_writer edit char <id> <name> | Edit a character |
| python -m novel_writer edit thread <id> <name> | Edit a plot thread |
| python -m novel_writer edit ch <id> <num> | Edit a chapter |
| python -m novel_writer interactive | Interactive REPL mode |

### Interactive Mode

```
python -m novel_writer interactive
```

Type `help` inside to see available commands.

### Typical Workflow

1. **Configure**: Set up API credentials
2. **Create**: Define your novel (title, genre, premise, target word count)
3. **Plan**: AI generates outline (characters, plot threads, chapter structure)
4. **Pipeline**: Runs Write -> Word-Count Check -> Review -> (Auto-Revise) -> Memory Update per chapter
5. **Consistency**: Final check across the entire novel

## Architecture

```
novel_writer/
  __main__.py          CLI and interactive entry point
  config.py            Configuration load/save
  agents/
    base.py            Base LLM agent with retry and JSON parsing
    planner.py         Novel outline generation
    writer.py          Chapter writing
    reviewer.py        Chapter review and scoring
    memory.py          Story memory management
  context/
    prompts.py         System and user prompt templates
    builder.py         Minimal-context assembly for each agent
  db/
    schema.py          SQLite schema and connection management
    repository.py      Data access layer
  workflow/
    orchestrator.py    Workflow coordination and pipeline logic
  requirements.txt
```

### Pipeline Flow

```
Plan -> [for each chapter: Write -> [Word-Count Check -> Rewrite] -> Review -> [Score < 65 -> Revise -> Re-review] -> Memory Update] -> Consistency Check
```

## Database Schema

SQLite database (novel_writer.db). Key tables:

- **novels**: Title, genre, language, premise, style guide, word count goal
- **characters**: Name, role, personality, appearance, background, arc, relationships (JSON)
- **chapters**: Number, title, outline, POV, characters, plot threads, status
- **chapter_contents**: Versioned content, summary, key events
- **plot_threads**: Name, description, status, related chapters
- **review_notes**: Issues, score, assessment per review round
- **world_entries**: World-building entries by category
- **global_memory**: Key-value store for plot threads, character arcs, foreshadowing

## Quality Controls

- **Review threshold**: Score below 65 triggers automatic revision (up to 2 rounds)
- **Word count**: Chapters flagged if outside [2500, 3500]; up to 3 automatic rewrites
- **Consistency check**: Final pass identifies continuity, character arc, timeline, and unresolved thread issues

## Configuration

Stored in ~/.novel_writer_config.json:

```json
{
  "api_key": "sk-...",
  "api_base": "https://api.deepseek.com/v1",
  "model": "deepseek-chat",
  "novels_dir": "./novels",
  "db_path": "./novel_writer.db"
}
```

## License

MIT
