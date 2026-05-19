# Research Literature Pipeline 中文说明

这是一个面向科研项目启动阶段的文献工作流项目，用来把 Codex、Zotero、MinerU PDF Router 和 Better BibTeX 串起来。

这个目录目前是 **项目模板 + 轻量 CLI + Codex skill 草稿**，不是完整插件。Zotero 继续作为 metadata、collection、tag、PDF 和 citation key 的主库；这个 repo 保存流程状态、筛选表、AI 易读 Markdown 缓存、阅读笔记、文献地图、prompt 和导出的 BibTeX。

## 什么东西放在哪里

- **Zotero**：metadata、collection、tag、PDF 附件、必要时的 Zotero note、Better BibTeX citation key。
- **这个 repo**：项目配置、候选文献表、筛选结果、MinerU Markdown 缓存、阅读笔记、文献地图、导出的 `.bib`。
- **MinerU**：把本地或远程 PDF 转成适合 AI 阅读的语义 Markdown。
- **Better BibTeX**：提供稳定 citation key 和首选 `.bib` 导出。

## Pipeline

1. **项目启动**
   - 创建项目目录。
   - 定义主题、范围、搜索词、Zotero collection 名、tag 和输出路径。

2. **文献发现与筛选**
   - 先收集候选文献 metadata。
   - 先筛选，再决定哪些文献导入 Zotero。
   - 使用 `must-read`、`method`、`background`、`maybe`、`exclude` 等状态。

3. **自动读文献**
   - 将筛选后的文献导入 Zotero。
   - 确保要阅读的每篇文献有 PDF 附件或本地 PDF 路径。
   - 用 MinerU 把 PDF 转成 Markdown。
   - 把 Markdown 保存为 `papers/<paper-id>/paper.md`。
   - 生成结构化阅读笔记 `notes/<paper-id>.md`。

4. **文献地图**
   - 默认用中文书写文献地图。
   - 汇总核心论文、方法、时间线、争议点、open questions 和写作引用计划。

5. **Better BibTeX 导出**
   - 优先使用 Better BibTeX 自动导出，以获得稳定 citation key。
   - 如果 Better BibTeX 还没配置好，使用 Zotero local API fallback。

## 重要：自动读文献需要 PDF 和 Markdown

Zotero 里可能只有 metadata。metadata 足够做筛选，但不够做全文自动阅读。

每一篇需要 AI 阅读的论文，项目里应该有：

```text
projects/<slug>/papers/<paper-id>/
  metadata.json
  paper.md
notes/<paper-id>.md
```

`paper.md` 不会从 Zotero 自动出现。它必须由 PDF 经过 MinerU 转换得到。PDF 来源可以是：

- Zotero 里已经保存的 PDF 附件；
- 从 arXiv、出版社页面、ADS、Semantic Scholar 等来源下载的 PDF；
- 你手动提供的本地 PDF。

如果 `paper.md` 缺失，AI 不应该声称已经读过全文。它应该先找到或下载 PDF，调用 MinerU，保存 Markdown，然后再生成阅读笔记。

对 arXiv 论文，如果能拿到 TeX 源码，TeX 有时比 PDF 更适合 AI 读取；没有 TeX 时再使用 PDF + MinerU。

## 目录结构

```text
research-literature-pipeline/
  README.md
  README.zh-CN.md
  scripts/research_pipeline.py
  templates/
  prompts/
  skills/research-literature-pipeline/SKILL.md
  projects/
```

每个研究项目的结构：

```text
projects/<slug>/
  project.toml
  data/candidates.jsonl
  data/screening.tsv
  papers/
  notes/
  maps/literature-map.md
  refs/
```

默认 `.gitignore` 会忽略 `projects/*`，因为真实项目文件可能包含你的研究方向、候选论文判断、笔记、PDF、MinerU Markdown 和 `.bib` 文件。公开 GitHub 仓库建议只同步 pipeline 本身；具体研究项目更适合放私有仓库或本地同步盘。

## 快速开始

创建一个新研究项目：

```bash
python3 scripts/research_pipeline.py init \
  --slug supernova-companion \
  --title "Type Ia Supernova Companion Constraints" \
  --topic "early light curve constraints on Type Ia supernova companion interaction"
```

添加一篇候选文献：

```bash
python3 scripts/research_pipeline.py add-candidate projects/supernova-companion \
  --doi 10.1038/nphys1170 \
  --title "Measured measurement" \
  --year 2009 \
  --status must-read \
  --reason "测试 Zotero 导入和笔记生成流程"
```

为 Zotero 中的一篇文献创建缓存目录和阅读笔记模板：

```bash
python3 scripts/research_pipeline.py paper-dir projects/supernova-companion \
  --key TTWH7MG8 \
  --title "Measured measurement" \
  --doi 10.1038/nphys1170
```

对一个已经有 PDF 附件的 Zotero 条目执行完整精读步骤：

```bash
python3 scripts/research_pipeline.py read-paper projects/supernova-companion \
  --key TTWH7MG8 \
  --language en
```

从本地 PDF 执行完整精读步骤：

```bash
python3 scripts/research_pipeline.py read-paper projects/supernova-companion \
  --title "Measured measurement" \
  --doi 10.1038/nphys1170 \
  --pdf /absolute/path/to/paper.pdf \
  --language en
```

如果已经有 MinerU Markdown，也可以直接导入：

```bash
python3 scripts/research_pipeline.py read-paper projects/supernova-companion \
  --key TTWH7MG8 \
  --title "Measured measurement" \
  --markdown /absolute/path/to/paper.md
```

检查哪些论文还没有完成 AI 阅读准备：

```bash
python3 scripts/research_pipeline.py audit projects/supernova-companion
```

对 `data/candidates.jsonl` 里筛选出的候选文献批量执行精读步骤：

```bash
python3 scripts/research_pipeline.py read-selected projects/supernova-companion \
  --statuses must-read,method,background \
  --limit 5
```

自动运行默认 pipeline 阶段：

```bash
python3 scripts/research_pipeline.py run projects/supernova-companion \
  --statuses must-read,method,background \
  --limit 5
```

`run` 会依次执行：

1. 项目结构校验；
2. 通过 `read-selected` 对筛选出的文献做全文精读；
3. 通过 `export-bib` 导出 BibTeX；
4. 通过 `audit` 检查是否缺 `paper.md` 或结构化笔记。

它不会在精读和 BibTeX 导出之间停下来等确认。如果部分文献缺 PDF，它会报告失败项，继续导出 `.bib`，最后用非零退出码提醒这些全文阅读产物仍未完成。

校验项目结构：

```bash
python3 scripts/research_pipeline.py validate projects/supernova-companion
```

通过 Zotero local API fallback 导出 BibTeX：

```bash
python3 scripts/research_pipeline.py export-bib projects/supernova-companion
```

## 推荐工作流

### 1. 项目启动

给 Codex 一个研究问题，例如：

```text
我想研究 Type Ia supernova early light curve constraints on companion interaction。
请帮我启动一个文献项目，生成关键词、筛选标准、Zotero collection/tag 方案和项目目录。
```

预期产物：

- `project.toml`
- 搜索关键词
- 筛选标准
- Zotero collection/tag 设计

### 2. 文献筛选

先只收集 metadata，不要一开始就把所有论文塞进 Zotero。

使用这些状态：

- `must-read`：必须读
- `method`：方法相关
- `background`：写 introduction 需要
- `maybe`：可能相关
- `exclude`：排除，并记录原因

筛选文件：

```text
data/candidates.jsonl
data/screening.tsv
```

### 3. 用 MinerU 把 PDF 转成 Markdown

将筛选后的文献导入 Zotero 后，先确认它有 PDF 附件或本地 PDF 路径。然后用 `mineru-pdf-router` 把 PDF 转为 Markdown。

CLI 可以对单篇论文直接执行这一步：

```bash
python3 scripts/research_pipeline.py read-paper projects/<slug> --key <ZOTERO_ITEM_KEY>
```

也可以对筛选后的候选文献批量执行：

```bash
python3 scripts/research_pipeline.py read-selected projects/<slug> --statuses must-read,method
```

这个命令会创建或更新：

```text
papers/<paper-id>/metadata.json
papers/<paper-id>/paper.pdf      # 当 PDF 来自 Zotero、--pdf 或 --pdf-url 时生成
papers/<paper-id>/paper.md
notes/<paper-id>.md
```

`read-selected` 能处理带有 `zotero_key`、`pdf_url` 或 arXiv 标识的候选文献。只有 DOI、没有 PDF 来源的候选文献会被报告为失败，因为 pipeline 不应该只凭 metadata 假装完成全文精读。

把 MinerU 输出保存到：

```text
projects/<slug>/papers/<paper-id>/paper.md
```

MinerU 输出是适合 AI 阅读的语义 Markdown，不是版面级复刻。如果要确认图表排版、页码、复杂公式或图像细节，仍然要回到原 PDF。

### 4. 阅读笔记

使用：

```text
prompts/read-paper-mineru.md
templates/reading-note.md
```

笔记保存到：

```text
notes/<paper-id>.md
```

### 5. 文献地图

更新：

```text
maps/literature-map.md
```

文献地图默认用中文书写，并包含：

- 核心问题
- 阅读优先级
- 领域时间线
- 方法分类
- 关键 claim 与证据
- 争议点
- open questions
- 写作引用计划

### 6. 导出 BibTeX

优先使用 Better BibTeX 自动导出，以获得稳定 citation key。

Fallback：

```bash
python3 scripts/research_pipeline.py export-bib projects/<slug>
```

正常跑 pipeline 时，优先用 `run`，而不是单独手动调用精读和导出：

```bash
python3 scripts/research_pipeline.py run projects/<slug>
```

## 隐私与 GitHub

不要提交：

- Zotero API key、MinerU token、代理配置、Cookie。
- Zotero 数据库，例如 `zotero.sqlite`。
- PDF、MinerU Markdown、真实 reading notes 或项目 `.bib`，除非你确定可以公开。
- 默认不要提交 `projects/*`。

默认忽略：

- `projects/*`
- `*.pdf`
- `*.xpi`
- `*.bib`
- `*.sqlite*`
- `.env*`
- `*.key`
- `*.token`
- `secrets/`
- `credentials/`

## 在另一台电脑上使用

1. 安装 Zotero。
2. 安装 Better BibTeX。
3. 配置 Codex Zotero MCP。
4. 配置 MinerU PDF Router。
5. 从 GitHub clone 本仓库。
6. 在 `research-literature-pipeline/` 内运行 CLI。

敏感配置放在每台机器自己的本地配置里，不要放进 GitHub。
