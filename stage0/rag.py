import os
import time
from pathlib import Path

import httpx
import numpy as np
import numpy.typing as npt

OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
EMBED_MODEL = "bge-m3"

ROOT = Path(__file__).resolve().parent.parent
TEXTS_DIR = ROOT / "stage0" / "texts"

QUESTIONS = [
    "Python-разработчик со знанием FastAPI",
    "remote AI engineer",
    "менеджер по продажам",
    "Senior Python разработчик в AI, Москва",
]

type Vectors = npt.NDArray[np.float32]


def load_texts() -> tuple[list[str], list[str]]:
    paths = sorted(TEXTS_DIR.glob("*.txt"))
    names = [p.name for p in paths]
    texts = [p.read_text(encoding="utf-8") for p in paths]
    return names, texts


def embed(client: httpx.Client, texts: list[str]) -> Vectors:
    response = client.post(
        "/api/embed",
        json={"model": EMBED_MODEL, "input": texts},
    )
    response.raise_for_status()
    vectors = response.json()["embeddings"]
    return np.array(vectors, dtype=np.float32)


def search(
    client: httpx.Client,
    doc_vectors: Vectors,
    names: list[str],
    question: str,
    k: int = 5,
) -> list[tuple[str, float]]:
    question_vector = embed(client, [question])[0]
    scores = doc_vectors @ question_vector
    top_indices = np.argsort(scores)[::-1][:k]
    return [(names[i], float(scores[i])) for i in top_indices]


if __name__ == "__main__":
    names, texts = load_texts()
    print(f"Загружено текстов: {len(texts)}")

    with httpx.Client(base_url=OLLAMA_URL, timeout=120) as client:
        start_time = time.perf_counter()
        doc_vectors = embed(client, texts)
        print(f"Эмбеддинги за {time.perf_counter() - start_time:.1f} с")
        print("Форма матрицы:", doc_vectors.shape)
        print("Нормы строк:", np.linalg.norm(doc_vectors, axis=1).round(4))

        for question in QUESTIONS:
            print(f"\nВопрос: {question}")
            for name, score in search(client, doc_vectors, names, question):
                print(f"   {score:.3f}  {name}")
