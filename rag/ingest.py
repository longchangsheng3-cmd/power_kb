from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any, Iterable

import chromadb
import yaml
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = Path(__file__).with_name("config.yaml")
DEFAULT_BATCH_SIZE = 64


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

        step = max(1, max_chars - overlap_chars)
        while len(current) > max_chars:
            chunks.append(current[:max_chars])
            current = current[step:]

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


def iter_documents(docs_dir: Path, max_chars: int, overlap_chars: int) -> Iterable[tuple[str, str, dict[str, Any]]]:
    for path in sorted(docs_dir.rglob("*.md")):
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            continue

        relative_path = path.relative_to(ROOT).as_posix()
        for index, chunk in enumerate(split_markdown(text, max_chars, overlap_chars)):
            document_id = hashlib.sha1(f"{relative_path}:{index}:{chunk}".encode("utf-8")).hexdigest()
            yield document_id, chunk, {"source": relative_path, "chunk": index}


def batched(items: list[Any], batch_size: int) -> Iterable[list[Any]]:
    for start in range(0, len(items), batch_size):
        yield items[start : start + batch_size]


def recreate_collection(client: chromadb.PersistentClient, collection_name: str):
    try:
        client.delete_collection(collection_name)
    except Exception as error:
        if error.__class__.__name__ != "NotFoundError":
            raise
    return client.get_or_create_collection(collection_name)


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Build local vector index for Markdown knowledge documents.")
    parser.add_argument("--keep-existing", action="store_true", help="Append to existing collection instead of rebuilding it.")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="Embedding/add batch size.")
    args = parser.parse_args()

    config = load_config()
    docs_dir = ROOT / config["docs_dir"]
    persist_dir = ROOT / config["persist_dir"]
    collection_name = config["collection_name"]
    chunk_config = config.get("chunk", {})

    if not docs_dir.exists():
        raise SystemExit(f"Docs directory not found: {docs_dir}")

    max_chars = int(chunk_config.get("max_chars", 900))
    overlap_chars = int(chunk_config.get("overlap_chars", 120))
    if max_chars <= 0:
        raise SystemExit("chunk.max_chars must be greater than 0.")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise SystemExit("chunk.overlap_chars must be >= 0 and smaller than chunk.max_chars.")

    records = list(iter_documents(docs_dir, max_chars, overlap_chars))
    if not records:
        print(f"No markdown chunks found under {docs_dir.relative_to(ROOT)}.")
        return

    print(f"Loading embedding model: {config['embedding_model']}")
    model = SentenceTransformer(config["embedding_model"])
    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = (
        client.get_or_create_collection(collection_name)
        if args.keep_existing
        else recreate_collection(client, collection_name)
    )

    ids = [record[0] for record in records]
    documents = [record[1] for record in records]
    metadatas = [record[2] for record in records]

    batch_size = max(1, args.batch_size)
    for id_batch, document_batch, metadata_batch in zip(
        batched(ids, batch_size),
        batched(documents, batch_size),
        batched(metadatas, batch_size),
    ):
        embeddings = model.encode(document_batch, normalize_embeddings=True).tolist()
        collection.add(ids=id_batch, documents=document_batch, metadatas=metadata_batch, embeddings=embeddings)

    source_count = len({metadata["source"] for metadata in metadatas})
    print(
        f"Indexed {len(documents)} chunks from {source_count} Markdown files "
        f"into {persist_dir.relative_to(ROOT)} / {collection_name}."
    )


if __name__ == "__main__":
    main()
