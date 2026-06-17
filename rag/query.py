from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import chromadb
import yaml
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = Path(__file__).with_name("config.yaml")


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def main() -> None:
    parser = argparse.ArgumentParser(description="Query the standby power knowledge base.")
    parser.add_argument("question", help="Question or issue description to retrieve related knowledge for.")
    parser.add_argument("--top-k", type=int, default=None, help="Number of chunks to return.")
    args = parser.parse_args()

    config = load_config()
    top_k = args.top_k or int(config.get("query", {}).get("top_k", 5))

    model = SentenceTransformer(config["embedding_model"])
    client = chromadb.PersistentClient(path=str(ROOT / config["persist_dir"]))
    collection = client.get_or_create_collection(config["collection_name"])

    query_embedding = model.encode([args.question], normalize_embeddings=True).tolist()[0]
    result = collection.query(query_embeddings=[query_embedding], n_results=top_k)

    print("# RAG 检索结果")
    print()
    print(f"问题：{args.question}")
    print()

    documents = result.get("documents", [[]])[0]
    metadatas = result.get("metadatas", [[]])[0]
    distances = result.get("distances", [[]])[0]

    if not documents:
        print("未检索到相关内容。请先执行 `python rag/ingest.py`。")
        return

    for index, document in enumerate(documents, start=1):
        metadata = metadatas[index - 1] or {}
        distance = distances[index - 1] if index - 1 < len(distances) else None
        score_line = f"相似距离：{distance:.4f}" if isinstance(distance, float) else "相似距离：N/A"
        print(f"## 片段 {index}")
        print()
        print(f"来源：{metadata.get('source', 'unknown')}")
        print(score_line)
        print()
        print(document.strip())
        print()


if __name__ == "__main__":
    main()
