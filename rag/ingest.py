from __future__ import annotations

import hashlib
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


def split_markdown(text: str, max_chars: int, overlap_chars: int) -> list[str]:
    blocks = [block.strip() for block in text.split("\n\n") if block.strip()]
    chunks: list[str] = []
    current = ""

    for block in blocks:
        candidate = f"{current}\n\n{block}".strip() if current else block
        if len(candidate) <= max_chars:
            current = candidate
            continue

        if current:
            chunks.append(current)
        current = block

        while len(current) > max_chars:
            chunks.append(current[:max_chars])
            current = current[max(0, max_chars - overlap_chars) :]

    if current:
        chunks.append(current)

    if overlap_chars <= 0 or len(chunks) <= 1:
        return chunks

    overlapped: list[str] = []
    previous_tail = ""
    for chunk in chunks:
        merged = f"{previous_tail}\n{chunk}".strip() if previous_tail else chunk
        overlapped.append(merged)
        previous_tail = chunk[-overlap_chars:]
    return overlapped


def iter_documents(docs_dir: Path, max_chars: int, overlap_chars: int):
    for path in sorted(docs_dir.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for index, chunk in enumerate(split_markdown(text, max_chars, overlap_chars)):
            relative_path = path.relative_to(ROOT).as_posix()
            document_id = hashlib.sha1(f"{relative_path}:{index}:{chunk}".encode("utf-8")).hexdigest()
            yield document_id, chunk, {"source": relative_path, "chunk": index}


def main() -> None:
    config = load_config()
    docs_dir = ROOT / config["docs_dir"]
    persist_dir = ROOT / config["persist_dir"]
    chunk_config = config.get("chunk", {})

    model = SentenceTransformer(config["embedding_model"])
    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_or_create_collection(config["collection_name"])

    collection.delete()
    collection = client.get_or_create_collection(config["collection_name"])

    ids: list[str] = []
    documents: list[str] = []
    metadatas: list[dict[str, Any]] = []

    for document_id, chunk, metadata in iter_documents(
        docs_dir,
        int(chunk_config.get("max_chars", 900)),
        int(chunk_config.get("overlap_chars", 120)),
    ):
        ids.append(document_id)
        documents.append(chunk)
        metadatas.append(metadata)

    if not documents:
        print("No markdown documents found.")
        return

    embeddings = model.encode(documents, normalize_embeddings=True).tolist()
    collection.add(ids=ids, documents=documents, metadatas=metadatas, embeddings=embeddings)
    print(f"Indexed {len(documents)} chunks from {docs_dir.relative_to(ROOT)}.")


if __name__ == "__main__":
    main()
