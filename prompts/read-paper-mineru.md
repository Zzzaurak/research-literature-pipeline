# 使用 MinerU 精读论文 Prompt

在 PDF 已经通过 `mineru-pdf-router` 转成 Markdown 后使用。

## 输入

- 项目主题：
- Zotero metadata：
- MinerU Markdown：

## 任务

把 Markdown 当作 PDF 的语义抽取结果来读。不要假设它完整保留了原 PDF 的视觉排版。

生成一份中文结构化阅读笔记，必须包含：

1. 为什么这篇论文重要。
2. 研究问题。
3. 主要论断。
4. 数据 / 样本。
5. 方法。
6. 关键图表 / 表格。
7. 局限性。
8. 和本项目的关系。
9. 可引用的论断。
10. 后续需要追踪的论文。

## 输出

按 `templates/reading-note.md` 的格式写入中文笔记。
