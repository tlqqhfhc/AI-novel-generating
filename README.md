
# novel-writer

AI 驱动的多智能体小说写作工具。使用一组专门的 AI 智能体（规划师、作家、审稿人、记忆库）逐章规划、写作、审阅和修订小说。

## 特性

- **多智能体流水线**：规划师、作家、审稿人和记忆库智能体自主协作
- **逐章写作**：每章在最小上下文中写作，以保持质量并处理长篇叙事
- **审阅与修订循环**：章节会自动审阅和修订，直到达到质量阈值
- **自动一致性检查**：最终检查情节漏洞、角色弧光问题和未解决的线索
- **字数控制**：可配置的目标字数决定章节数；写前字数检查（目标 2500-3500 字）触发自动重写
- **交互模式**：通过 CLI 提示符运行完整流水线或单独步骤
- **编辑命令**：无需重启即可修改小说信息、角色、情节线索和章节
- **记忆管理**：每章跟踪关键事件、角色发展和情节线索进展
- **SQLite 存储**：所有小说、章节、角色和审阅数据都存储在本地

## 环境要求

- Python 3.10+
- 兼容 OpenAI 接口的 API（已在 DeepSeek 上测试，适用于任何兼容 OpenAI 接口的提供商）

## 快速开始

```
pip install openai rich
```

```
python -m novel_writer configure
```

系统将提示你输入：
- API 密钥
- Base URL（默认为 https://api.deepseek.com/v1）
- 模型名称（默认为 deepseek-chat）

配置将保存到 ~/.novel_writer_config.json。

## 用法

### CLI 命令

| 命令 | 描述 |
|---|---|
| python -m novel_writer configure | 设置 API 密钥和模型 |
| python -m novel_writer create | 创建一部新小说 |
| python -m novel_writer list | 列出所有小说 |
| python -m novel_writer plan <id> | 使用 AI 生成大纲 |
| python -m novel_writer status <id> | 显示小说进度 |
| python -m novel_writer write <id> [ch] | 撰写一章 |
| python -m novel_writer review <id> <ch> | 审阅一章 |
| python -m novel_writer pipeline <id> [s] [e] | 运行完整流水线 |
| python -m novel_writer pipeline:1 <id> <ch> | 为一章运行流水线 |
| python -m novel_writer consistency <id> | 最终一致性检查 |
| python -m novel_writer edit novel <id> | 编辑小说信息 |
| python -m novel_writer edit char <id> <name> | 编辑角色 |
| python -m novel_writer edit thread <id> <name> | 编辑情节线索 |
| python -m novel_writer edit ch <id> <num> | 编辑某一章 |
| python -m novel_writer export <id> | 将完整小说导出为 Markdown 文件存储在novel文件夹中 |
| python -m novel_writer interactive | 交互式 REPL 模式 |

### 交互模式

```
python -m novel_writer interactive
```

进入后输入 `help` 查看可用命令。

### 典型工作流程

1. **配置**：设置 API 凭证
2. **创建**：定义你的小说（标题、类型、前提、目标字数）
3. **规划**：AI 生成大纲（角色、情节线索、章节结构）
4. **流水线**：每章依次执行 写作 -> 字数检查 -> 审阅 -> (自动修订) -> 记忆更新
5. **一致性检查**：对整个小说进行最终检查

## 架构

```
novel_writer/
  __main__.py          CLI 和交互入口
  config.py            配置加载/保存
  agents/
    base.py            基础 LLM 智能体，带重试和 JSON 解析
    planner.py         小说大纲生成
    writer.py          章节写作
    reviewer.py        章节审阅和评分
    memory.py          故事记忆管理
  context/
    prompts.py         系统和用户提示模板
    builder.py         为各智能体组装最小上下文
  db/
    schema.py          SQLite 模式与连接管理
    repository.py      数据访问层
  workflow/
    orchestrator.py    工作流协调与流水线逻辑
  requirements.txt
```

### 流水线流程

```
规划 -> [对每一章：写作 -> [字数检查 -> 重写] -> 审阅 -> [分数 < 65 -> 修订 -> 重新审阅] -> 记忆更新] -> 一致性检查
```

## 数据库模式

SQLite 数据库（novel_writer.db）。主要表：

- **novels**：标题、类型、语言、前提、风格指南、字数目标
- **characters**：姓名、角色、性格、外貌、背景、弧光、关系（JSON）
- **chapters**：编号、标题、大纲、视角、角色、情节线索、状态
- **chapter_contents**：版本化内容、摘要、关键事件
- **plot_threads**：名称、描述、状态、相关章节
- **review_notes**：每轮审阅的问题、分数、评估
- **world_entries**：按类别划分的世界构建条目
- **global_memory**：用于情节线索、角色弧光、伏笔的键值存储

## 质量控制

- **审阅阈值**：分数低于 65 分将触发自动修订（最多 2 轮）
- **字数检查**：章节字数超出 [2500, 3500] 区间会被标记；最多 3 次自动重写
- **一致性检查**：最终检查识别连贯性、角色弧光、时间线和未解决线索等问题

## 配置

保存在 ~/.novel_writer_config.json：

```json
{
  "api_key": "sk-...",
  "api_base": "https://api.deepseek.com/v1",
  "model": "deepseek-chat",
  "novels_dir": "./novels",
  "db_path": "./novel_writer.db"
}
```

## 许可证

MIT
