"""FAISS-backed vector index helpers for image retrieval."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path


VECTOR_INDEX_DIMENSION = 512


def _load_vector_dependencies():
    """Load FAISS and NumPy lazily to keep import-time light."""

    try:
        import faiss
        import numpy as np
    except ImportError as exc:
        raise ImportError(
            "Vector indexing requires faiss-cpu and numpy. Install them with "
            "`pip install -r requirements.txt`."
        ) from exc

    return faiss, np


def get_vector_index_directory():
    """Return the on-disk directory used for FAISS data and metadata."""

    base_path = Path(__file__).resolve().parent
    vector_index_dir = base_path / "vector_index_data"
    vector_index_dir.mkdir(parents=True, exist_ok=True)
    return vector_index_dir


def get_index_file_path():
    """Return the FAISS index file path."""

    return get_vector_index_directory() / "image_vectors.faiss"


def get_metadata_file_path():
    """Return the metadata JSON file path used alongside the FAISS index."""

    return get_vector_index_directory() / "image_vectors.json"


def _create_empty_index():
    """Create an empty inner-product FAISS index for normalized vectors."""

    faiss, _ = _load_vector_dependencies()
    return faiss.IndexFlatIP(VECTOR_INDEX_DIMENSION)


def load_index():
    """Load the FAISS index from disk, or create a new empty one."""

    faiss, _ = _load_vector_dependencies()
    index_file_path = get_index_file_path()

    if index_file_path.exists():
        return faiss.read_index(str(index_file_path))

    return _create_empty_index()


def save_index(index):
    """Persist the FAISS index to disk."""

    faiss, _ = _load_vector_dependencies()
    faiss.write_index(index, str(get_index_file_path()))


def load_metadata():
    """Load metadata records aligned with FAISS vector positions."""

    metadata_file_path = get_metadata_file_path()
    if not metadata_file_path.exists():
        return []

    return json.loads(metadata_file_path.read_text(encoding="utf-8"))


def save_metadata(metadata_records):
    """Persist metadata records aligned with FAISS vector positions."""

    metadata_file_path = get_metadata_file_path()
    metadata_file_path.write_text(
        json.dumps(metadata_records, indent=2),
        encoding="utf-8",
    )


def upsert_embedding(image_id, embedding, metadata):
    """Insert or update one normalized embedding in the FAISS index.

    Because the simple `IndexFlatIP` index does not support true deletion,
    updates rebuild the index from the full in-memory metadata list. This keeps
    the implementation straightforward while remaining good enough for the
    current project scale.
    """

    _, np = _load_vector_dependencies()
    normalized_embedding = np.asarray(embedding, dtype="float32")
    index = load_index()
    metadata_records = load_metadata()

    new_record = {
        "image_id": image_id,
        "embedding": normalized_embedding.tolist(),
        "metadata": deepcopy(metadata),
    }

    updated = False
    for idx, record in enumerate(metadata_records):
        if record["image_id"] == image_id:
            metadata_records[idx] = new_record
            updated = True
            break

    if not updated:
        metadata_records.append(new_record)

    rebuilt_index = _create_empty_index()
    if metadata_records:
        vectors = np.asarray(
            [record["embedding"] for record in metadata_records],
            dtype="float32",
        )
        rebuilt_index.add(vectors)

    save_index(rebuilt_index)
    save_metadata(metadata_records)
    return {
        "image_id": image_id,
        "metadata": deepcopy(metadata),
    }


def search_similar_vectors(query_embedding, top_k=5):
    """Search the FAISS index with a normalized query vector."""

    _, np = _load_vector_dependencies()
    index = load_index()
    metadata_records = load_metadata()

    if index.ntotal == 0 or not metadata_records:
        return []

    query = np.asarray([query_embedding], dtype="float32")
    distances, indices = index.search(query, top_k)

    results = []
    for score, idx in zip(distances[0], indices[0]):
        if idx < 0 or idx >= len(metadata_records):
            continue

        record = metadata_records[idx]
        results.append(
            {
                "image_id": record["image_id"],
                "score": float(score),
                "image_path": record["metadata"].get("image_path"),
            }
        )

    return results
