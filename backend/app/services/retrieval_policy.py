from __future__ import annotations


def filter_relevant(results: list[dict]) -> list[dict]:
    if not results:
        return []
    top_score = float(results[0].get("score", 0.0))
    threshold = max(0.2, top_score * 0.3)
    return [
        item
        for index, item in enumerate(results)
        if index == 0 or float(item.get("score", 0.0)) >= threshold
    ]
