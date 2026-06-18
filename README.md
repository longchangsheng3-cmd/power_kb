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
│  ├─ db/                    # 本地向量库目录，运行后生成
│  └─ index/                 # 检索结果缓存，运行后生成
├─ prompts/                  # Claude Code 提示词模板
├─ inputs/                   # 输入材料：日志、报告等
├─ outputs/                  # 输出分析报告与摘要
└─ scripts/                  # 辅助脚本
```

## 快速开始

### 1. 安装依赖

建议使用 Python 3.10+。

```powershell
pip install -r requirements.txt
```

### 2. 构建本地索引

```powershell
python rag/ingest.py
```

默认会扫描 `docs/` 下所有 Markdown 文件，切分为知识片段，使用 `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` 生成 embedding，并写入本地 ChromaDB：`rag/db/`。

### 3. 查询知识库

```powershell
python rag/query.py "待机电流偏高，wlan wakelock 持续 active，怎么分析？"
```

查询结果会输出到终端，并默认保存到：

```text
rag/index/last_query.md
```

可选参数：

```powershell
python rag/query.py "待机电流偏高怎么分析？" --top-k 8
python rag/query.py "Wi-Fi 待机周期性唤醒" --output outputs/analysis/wifi-query.md
python rag/query.py "suspend 失败怎么排查？" --no-save
```

### 4. 结合 Claude Code 分析

1. 将日志放入 `inputs/logs/`。
2. 使用 `rag/query.py` 检索相关知识。
3. 将检索结果和日志一起交给 Claude Code。
4. 按 `prompts/analyze-standby-issue.md` 输出分析报告。
5. 有复用价值的结论沉淀到 `docs/cases/`。
6. 重新执行 `python rag/ingest.py` 更新索引。

## V0.2 本地 Markdown RAG 检索

### 当前能力

- 扫描 `docs/` 下的 Markdown 文档。
- 按段落和字符长度切分 chunk。
- 使用本地 sentence-transformers 模型生成向量。
- 使用 ChromaDB 本地持久化向量库。
- 支持命令行检索 Top-K 相关片段。
- 输出来源文件、chunk 编号、相似距离和片段内容。
- 默认保存最近一次查询结果，便于复制给 Claude Code。

### 配置文件

RAG 配置集中在 `rag/config.yaml`：

```yaml
docs_dir: docs
persist_dir: rag/db
collection_name: standby_power_kb
embedding_model: sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
chunk:
  max_chars: 900
  overlap_chars: 120
query:
  top_k: 5
```

### 验收命令

```powershell
pip install -r requirements.txt
python rag/ingest.py
python rag/query.py "待机电流高，wlan wakelock 持续 active 怎么分析？"
```

能看到 `# RAG 检索结果`，并且片段来源包含 `docs/checklist/` 或 `docs/cases/`，即表示 V0.2 基础流程可用。

### 注意事项

- 第一次运行会下载 embedding 模型，耗时取决于网络环境。
- `rag/db/` 和 `rag/index/` 是本地运行产物，不提交到 Git。
- 每次更新 `docs/` 后，需要重新执行 `python rag/ingest.py`。
- 如果只想追加索引而不是重建，可使用 `python rag/ingest.py --keep-existing`。

## V0.3 日志辅助分析和标准报告输出

### 当前能力

- 从日志文件中提取待机功耗相关关键行。
- 按 `wakelock`、`wakeup`、`suspend`、`network`、`power-rail`、`error` 等分类统计线索。
- 将问题描述、日志证据、RAG 检索结果和分析模板打包为 Claude Code 分析上下文。
- 生成标准待机功耗分析报告草稿。

### 使用流程

先准备日志文件，例如：

```text
inputs/logs/example.log
```

执行日志辅助分析：

```powershell
python scripts/analyze_log.py inputs/logs/example.log --context-lines 1 --output outputs/analysis/log_extract.md
```

执行 RAG 检索：

```powershell
python rag/query.py "待机电流高，wlan wakelock 持续 active 怎么分析？" --output outputs/analysis/rag_result.md
```

生成 Claude Code 分析上下文：

```powershell
python scripts/build_analysis_context.py `
  --issue "待机电流高，wlan wakelock 持续 active" `
  --platform "Android/Linux 示例平台" `
  --scenario "连接 Wi-Fi 后锁屏静置" `
  --current "期望待补充，实测待补充" `
  --log-extract outputs/analysis/log_extract.md `
  --rag-result outputs/analysis/rag_result.md `
  --output outputs/analysis/analysis_context.md
```

生成标准报告草稿：

```powershell
python scripts/create_analysis_report.py `
  --issue "待机电流高，wlan wakelock 持续 active" `
  --context outputs/analysis/analysis_context.md `
  --log-extract outputs/analysis/log_extract.md `
  --rag-result outputs/analysis/rag_result.md `
  --output outputs/analysis/analysis_report.md
```

### 验收标准

完成后应生成以下文件：

- `outputs/analysis/log_extract.md`
- `outputs/analysis/rag_result.md`
- `outputs/analysis/analysis_context.md`
- `outputs/analysis/analysis_report.md`

其中 `analysis_context.md` 可直接复制给 Claude Code，用于输出最终分析报告；`analysis_report.md` 是本地生成的标准报告草稿。

## V0.3.1 结构化结论与人工确认入库

### 当前能力

- 在 V0.3 日志提取基础上，自动聚合 Top active wake locks、Pending Wakeup Sources、SPM wakeup reasons 和 USB/Type-C/Charging 证据。
- 将日志、RAG 知识和报告模板整理成 Claude Code 分析上下文。
- 生成结构化分析结论，包含可能原因排序、关键依据、下一步验证和人工复核清单。
- 人工确认结论正确后，将结论沉淀为 `docs/cases/` 案例。
- 重新执行 `python rag/ingest.py` 后，新案例会进入本地向量存储库。

### 分析闭环

1. 运行日志提取和 RAG 检索。
2. 生成 `analysis_context.md`，交给 Claude Code 分析。
3. 生成或修订 `structured_conclusion.md`。
4. 人工复核结论是否正确。
5. 确认后执行 `scripts/confirm_case.py --confirmed` 入库。
6. 执行 `python rag/ingest.py` 更新向量库。

### 结构化结论生成

```powershell
python scripts/generate_structured_conclusion.py `
  --issue "待机耗电高，分析 kernel log 中可能原因" `
  --log-extract outputs/analysis/real_log_extract.md `
  --rag-result outputs/analysis/real_rag_result.md `
  --output outputs/analysis/structured_conclusion.md `
  --case-hint
```

### 人工确认后入库

只有人工确认结论正确后，才执行：

```powershell
python scripts/confirm_case.py `
  --confirmed `
  --title "待机耗电高 - USB wake lock 长时间活跃" `
  --issue "待机耗电高，kernel log 显示 USB wake lock 长时间 active" `
  --conclusion outputs/analysis/structured_conclusion.md `
  --source-log inputs/logs/kernel_log_12__2026_0617_174148 `
  --reviewer "longchangsheng"
```

然后更新本地向量库：

```powershell
python rag/ingest.py
```

## 迭代路线

- V0.1：知识库骨架、基础文档、案例模板、Claude Code 工作流。
- V0.2：本地 Markdown RAG 检索。
- V0.3：日志辅助分析和标准报告输出。
- V0.4：案例自动生成草稿。
- V0.5：团队文档同步或 Web UI。
