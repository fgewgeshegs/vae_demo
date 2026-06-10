"""文档切片器 - 将文本切分为适合 Embedding 的块"""

from __future__ import annotations

import re
from typing import List, Dict


class TextChunker:
    """文本切片器"""

    def __init__(self, chunk_size: int = 500, overlap: int = 50):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str, metadata: dict | None = None) -> List[Dict]:
        """将文本切分为多个块"""
        if not text.strip():
            return []

        # 按段落分割
        paragraphs = re.split(r"\n\s*\n", text)
        chunks = []
        current_chunk = ""
        current_size = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            para_size = len(para)

            if current_size + para_size <= self.chunk_size:
                current_chunk += para + "\n\n"
                current_size += para_size
            else:
                if current_chunk:
                    chunks.append({
                        "content": current_chunk.strip(),
                        "metadata": metadata or {},
                    })
                current_chunk = para + "\n\n"
                current_size = para_size

        if current_chunk:
            chunks.append({
                "content": current_chunk.strip(),
                "metadata": metadata or {},
            })

        # 添加 index 信息
        for i, chunk in enumerate(chunks):
            chunk["chunk_index"] = i

        return chunks
