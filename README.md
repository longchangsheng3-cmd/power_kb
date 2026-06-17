# 待机功耗分析与优化知识库

这是一个结合 Claude Code 与本地 RAG 的待机功耗分析知识库基础版。

## 目标

- 沉淀待机功耗分析、优化、验证相关知识。
- 通过 RAG 检索历史案例、检查清单和基础知识。
- 辅助 Claude Code 基于资料输出结构化分析报告。
- 先构建本地基础版，再逐步迭代日志解析、案例归档和团队协作能力。

## 目录结构

```text
.
├─ AGENTS.md                 # Claude Code 工作说明
├─ docs/                     # 知识库正文
│  ├─ basics/                # 基础知识
│  ├─ checklist/             # 排查清单
│  ├─ cases/                 # 问题案例
│  ├─ optimization/          # 优化策略
│  └─ glossary/              # 术语表
├─ rag/                      # 本地 RAG 脚本与索引
│  ├─ ingest.py              # 文档入库
│  ├─ query.py               # 检索查询
│  ├─ config.yaml            # RAG 配置
│  ├─ db/                    # 本地向量库目录
│  └─ index/                 # 检索结果/索引辅助文件
├─ prompts/                  # Claude Code 提示词模板
├─ inputs/                   # 输入材料：日志、报告等
├─ outputs/                  # 输出分析报告与摘要
└─ scripts/                  # 辅助脚本
```

## 快速开始

### 1. 安装依赖

建议使用 Python 3.10+。

```powershell
pip install chromadb sentence-transformers pyyaml
```

### 2. 构建本地索引

```powershell
python rag/ingest.py
```

### 3. 查询知识库

```powershell
python rag/query.py "待机电流偏高，wlan wakelock 持续 active，怎么分析？"
```

### 4. 结合 Claude Code 分析

1. 将日志放入 `inputs/logs/`。
2. 使用 `rag/query.py` 检索相关知识。
3. 将检索结果和日志一起交给 Claude Code。
4. 按 `prompts/analyze-standby-issue.md` 输出分析报告。
5. 有复用价值的结论沉淀到 `docs/cases/`。
6. 重新执行 `python rag/ingest.py` 更新索引。

## 迭代路线

- V0.1：知识库骨架、基础文档、案例模板、Claude Code 工作流。
- V0.2：本地 Markdown RAG 检索。
- V0.3：日志辅助分析和标准报告输出。
- V0.4：案例自动生成草稿。
- V0.5：团队文档同步或 Web UI。
