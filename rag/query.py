from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import chromadb
import yaml
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = Path(__file__).with_name("config.yaml")
DEFAULT_OUTPUT = ROOT / "rag" / "index" / "last_query.md"


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def format_results(question: str, result: dict[str, Any]) -> str:
    lines = ["# RAG 检索结果", "", f"问题：{question}", ""]

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    if not documents:
        lines.append("未检索到相关内容。请先执行 `python rag/ingest.py`。")
        return "\n".join(lines).rstrip() + "\n"

    for index, document in enumerate(documents, start=1):
        metadata = metadatas[index - 1] or {}
        distance = distances[index - 1] if index - 1 < len(distances) else None
        score_line = f"相似距离：{distance:.4f}" if isinstance(distance, float) else "相似距离：N/A"
        lines.extend(
            [
                f"## 片段 {index}",
                "",
                f"来源：{metadata.get('source', 'unknown')}",
                f"Chunk：{metadata.get('chunk', 'unknown')}",
                score_line,
                "",
                document.strip(),
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Query the standby power knowledge base.")
    parser.add_argument("question", help="Question or issue description to retrieve related knowledge for.")
    parser.add_argument("--top-k", type=int, default=None, help="Number of chunks to return.")
    parser.add_argument("--output", type=Path, default=None, help="Optional Markdown file to save query results.")
    parser.add_argument("--no-save", action="store_true", help="Do not save results to rag/index/last_query.md.")
    args = parser.parse_args()

    config = load_config()
    top_k = args.top_k or int(config.get("query", {}).get("top_k", 5))
    if top_k <= 0:
        raise SystemExit("--top-k must be greater than 0.")

    persist_dir = ROOT / config["persist_dir"]
    if not persist_dir.exists():
        raise SystemExit("Vector store not found. Run `python rag/ingest.py` first.")

    print(f"Loading embedding model: {config['embedding_model']}")
    model = SentenceTransformer(config["embedding_model"])
    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_or_create_collection(config["collection_name"])

    if collection.count() == 0:
        raise SystemExit("Vector store is empty. Run `python rag/ingest.py` first.")

    query_embedding = model.encode([args.question], normalize_embeddings=True).tolist()[0]
    result = collection.query(query_embeddings=[query_embedding], n_results=top_k)
    output = format_results(args.question, result)
    print(output)

    if not args.no_save:
        output_path = (args.output or DEFAULT_OUTPUT).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output, encoding="utf-8")
        print(f"Saved query result to {output_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
