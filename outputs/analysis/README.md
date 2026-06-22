# 分析输出目录

该目录用于保存 V0.3 日志辅助分析和标准报告输出。

## 常见文件

| 文件 | 来源 | 说明 |
|---|---|---|
| `log_extract.md` | `scripts/analyze_log.py` | 日志关键行和分类统计 |
| `rag_result.md` | `rag/query.py` | RAG 检索结果 |
| `analysis_context.md` | `scripts/build_analysis_context.py` | 可复制给 Claude Code 的完整分析上下文 |
| `structured_conclusion.md` | `scripts/generate_structured_conclusion.py` | 结构化分析结论，供人工复核 |
| `case_draft.md` | `scripts/generate_case_draft.py` | 可编辑案例草稿，人工确认后入库 |
| `analysis_report.md` | `scripts/create_analysis_report.py` | 标准分析报告草稿 |

## 建议

- 临时分析文件默认不提交到 Git。
- 有复用价值的最终结论应沉淀到 `docs/cases/`。
