# Research Literature Pipeline 中文说明

这是一个面向科研项目启动阶段的文献工作流项目，用来把 Codex、Zotero、MinerU PDF Router 和 Better BibTeX 串起来。

目标流程：

1. 项目启动
2. 文献发现与筛选
3. 自动读文献
4. 生成文献地图
5. 导出 Better BibTeX / BibTeX `.bib`

这个目录目前是 **项目模板 + 轻量 CLI + Codex skill 草稿**，不是完整插件。这样做更容易同步到 GitHub，也方便在另一台电脑上拉下来后继续使用。

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
projects/<项目名>/
  project.toml
  data/candidates.jsonl
  data/screening.tsv
  papers/
  notes/
  maps/literature-map.md
  refs/
```

默认 `.gitignore` 会忽略 `projects/*`，因为这些文件可能包含你的研究方向、候选论文、笔记、PDF、MinerU Markdown 和参考文献库。公开 GitHub 仓库建议只同步模板、脚本和 prompt；具体研究项目更适合放私有仓库或本地同步盘。

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

为 Zotero 中的一篇文献创建缓存目录和笔记模板：

```bash
python3 scripts/research_pipeline.py paper-dir projects/supernova-companion \
  --key TTWH7MG8 \
  --title "Measured measurement" \
  --doi 10.1038/nphys1170
```

校验项目结构：

```bash
python3 scripts/research_pipeline.py validate projects/supernova-companion
```

导出 BibTeX：

```bash
python3 scripts/research_pipeline.py export-bib projects/supernova-companion
```

## 推荐工作流

### 1. 项目启动

给 Codex 一个研究问题，例如：

```text
我想研究 Type Ia supernova early light curve constraints on companion interaction。
请帮我启动一个文献项目，生成关键词、筛选标准和 Zotero collection/tag 方案。
```

产物：

- `project.toml`
- 搜索关键词
- 筛选标准
- Zotero collection/tag 设计

### 2. 文献筛选

先只收集 metadata，不要一开始就把所有论文塞进 Zotero。

候选文献建议分成：

- `must-read`：必须读
- `method`：方法相关
- `background`：写 introduction 需要
- `maybe`：可能相关
- `exclude`：排除，并记录原因

筛选结果保存在：

```text
data/candidates.jsonl
data/screening.tsv
```

### 3. 自动读文献

Zotero 负责保存 metadata 和 PDF。AI 易读文本保存在项目目录。

推荐每篇论文缓存：

```text
papers/<paper-id>/
  metadata.json
  paper.md
notes/<paper-id>.md
```

其中 `paper.md` 来自 MinerU PDF Router 的 Markdown 输出。

### 4. 使用 MinerU 转 PDF

当 Zotero 中有 PDF 后，用 `mineru-pdf-router` 把 PDF 转成 Markdown。MinerU 输出更适合 AI 阅读、总结和问答，但它不是排版级复刻；如果要检查图表布局，仍然要回到原 PDF。

建议把 MinerU 输出保存为：

```text
projects/<项目名>/papers/<paper-id>/paper.md
```

然后用：

```text
prompts/read-paper-mineru.md
```

生成结构化阅读笔记。

### 5. 文献地图

多篇论文读完后，更新：

```text
maps/literature-map.md
```

文献地图应包含：

- 核心问题
- 阅读优先级
- 领域时间线
- 方法分类
- 关键 claim 与证据
- 争议点
- open questions
- 写作引用计划

### 6. 导出 `.bib`

优先使用 Better BibTeX 的自动导出，以获得稳定 citation key。

如果 Better BibTeX 还没配置好，可以先用脚本的 Zotero local API fallback：

```bash
python3 scripts/research_pipeline.py export-bib projects/<项目名>
```

## 隐私与 GitHub

公开 GitHub 前请注意：

- 不要提交 Zotero API key、MinerU token、代理配置、Cookie。
- 不要提交 Zotero 数据库，例如 `zotero.sqlite`。
- 不要提交 PDF、MinerU Markdown、真实 reading notes，除非你确定可以公开。
- 不要默认提交 `projects/*`；里面可能包含未发表研究方向和文献判断。
- `.bib` 也可能暴露你的研究主题，公开前检查是否合适。

当前仓库默认忽略这些内容：

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
2. 安装 Better BibTeX 插件。
3. 配置 Codex 的 Zotero MCP。
4. 配置 MinerU PDF Router。
5. 从 GitHub 克隆本项目。
6. 在 `research-literature-pipeline/` 内运行 CLI。

敏感配置不要放进 GitHub，应放在每台机器自己的本地配置里。
