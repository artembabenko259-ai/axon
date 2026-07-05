"""Local fast keyword and semantic TF-IDF search index for AXON codebase."""

from __future__ import annotations

import math
import re
from pathlib import Path

# Directories to ignore
IGNORE_DIRS = {
    ".git", ".axon", "node_modules", "venv", "env", "__pycache__",
    "build", "dist", ".next", "out", "target", "obj", "bin"
}

# Supported file extensions
SUPPORTED_EXTS = {
    ".py", ".go", ".ts", ".tsx", ".js", ".jsx", ".cpp", ".hpp",
    ".h", ".c", ".rs", ".java", ".cs", ".md", ".json", ".yaml", ".yml"
}


def tokenize(text: str) -> list[str]:
    """Tokenizes text into alphanumeric lowercase words."""
    return re.findall(r"[a-z0-9_]+", text.lower())


class CodeSearchIndex:
    """TF-IDF based search engine for code chunks in the workspace."""

    def __init__(self, workspace_path: str | Path) -> None:
        self.workspace = Path(workspace_path)
        self.chunks: list[dict[str, any]] = []  # List of chunks: {file, start_line, text, tokens}
        self.doc_freqs: dict[str, int] = {}     # Word -> document frequency
        self.num_docs = 0

    def build(self) -> int:
        """Walks the workspace, creates chunks, and computes TF-IDF doc frequencies."""
        self.chunks.clear()
        self.doc_freqs.clear()

        try:
            for p in self.workspace.rglob("*"):
                if any(part in IGNORE_DIRS for part in p.parts):
                    continue
                if p.is_file() and p.suffix in SUPPORTED_EXTS:
                    self._index_file(p)
        except Exception as exc:
            print(f"[search index error] {exc}")

        self.num_docs = len(self.chunks)
        # Compute Document Frequencies
        for chunk in self.chunks:
            unique_tokens = set(chunk["tokens"])
            for t in unique_tokens:
                self.doc_freqs[t] = self.doc_freqs.get(t, 0) + 1

        return self.num_docs

    def _index_file(self, file_path: Path) -> None:
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return

        lines = content.splitlines()
        rel_path = file_path.relative_to(self.workspace).as_posix()
        
        # Chunking: 15 lines per chunk, with 5 lines overlap
        chunk_size = 15
        overlap = 5
        
        idx = 0
        while idx < len(lines):
            chunk_lines = lines[idx : idx + chunk_size]
            chunk_text = "\n".join(chunk_lines)
            tokens = tokenize(chunk_text)
            
            if tokens:
                self.chunks.append({
                    "file": rel_path,
                    "start_line": idx + 1,
                    "text": chunk_text,
                    "tokens": tokens
                })
            idx += (chunk_size - overlap)

    def search(self, query: str, limit: int = 4) -> list[dict[str, any]]:
        """Searches index for matching chunks, sorted by cosine similarity."""
        query_tokens = tokenize(query)
        if not query_tokens or self.num_docs == 0:
            return []

        # Compute query TF
        query_tf = {}
        for t in query_tokens:
            query_tf[t] = query_tf.get(t, 0.0) + 1.0

        # Compute IDF for query terms
        query_idf = {}
        for t in query_tf:
            df = self.doc_freqs.get(t, 0)
            # Smooth IDF
            query_idf[t] = math.log((self.num_docs + 1) / (df + 1)) + 1.0

        # Calculate scores
        results = []
        for chunk in self.chunks:
            chunk_tokens = chunk["tokens"]
            chunk_tf = {}
            for t in chunk_tokens:
                chunk_tf[t] = chunk_tf.get(t, 0.0) + 1.0

            # Compute dot product and magnitude
            dot_product = 0.0
            chunk_magnitude = 0.0
            
            # Since we only score terms present in the query
            for t in query_tf:
                if t in chunk_tf:
                    # tf-idf weights
                    w_q = query_tf[t] * query_idf[t]
                    w_d = chunk_tf[t] * query_idf[t]
                    dot_product += (w_q * w_d)

            # Document magnitude (using IDF weights)
            for t in chunk_tf:
                df = self.doc_freqs.get(t, 0)
                idf = math.log((self.num_docs + 1) / (df + 1)) + 1.0
                w_d = chunk_tf[t] * idf
                chunk_magnitude += (w_d * w_d)

            if dot_product > 0.0 and chunk_magnitude > 0.0:
                score = dot_product / math.sqrt(chunk_magnitude)
                results.append((score, chunk))

        # Sort by score descending
        results.sort(key=lambda x: x[0], reverse=True)
        
        # Format output
        outputs = []
        for score, chunk in results[:limit]:
            outputs.append({
                "file": chunk["file"],
                "start_line": chunk["start_line"],
                "text": chunk["text"],
                "score": score
            })
        return outputs
