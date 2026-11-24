import os
from pathlib import Path
import time

import httpx
import numpy as np

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = "bge-m3"

ROOT = Path(__file__).resolve().parent.parent
TEXTS_DIR = ROOT / "stage0" / "texts"
DATA_DIR = ROOT / "data"

def load_texts() -> tuple[list[str], list[str]]:
    paths = sorted(TEXTS_DIR.glob("*.txt"))
    names = [p.name for p in paths]
    texts = [p.read_text(encoding="utf-8") for p in paths]
    return names, texts

def embed(client: httpx.Client, texts: list[str]) -> np.ndarray:
    response = client.post(
        "/api/embed",
        json={"model": EMBED_MODEL, "input": texts},
    )
    response.raise_for_status()
    vectors = response.json()["embeddings"]
    return np.array(vectors, dtype=np.float32)

if __name__ == "__main__":
    names, texts = load_texts()
    print(f"Загружено текстов: {len(texts)}")

    with httpx.Client(base_url=OLLAMA_URL, timeout=120) as client:
        start_time = time.perf_counter()
        vectors = embed(client, texts)
        print(f"Эмбеддинги за {time.perf_counter() - start_time:.1f} с")

    print("Форма матрицы:", vectors.shape)
    print("Нормы строк:", np.linalg.norm(vectors, axis=1).round(4))