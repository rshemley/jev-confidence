#!/usr/bin/env python3
"""Minimal Jev fact-weighting example (stdlib only).

Sends one fact to typesafe/jev-1.13 via the OpenRouter Decisions API and
prints the calibrated weight (0..1).

Usage:
    export OPENROUTER_API_KEY=sk-or-...
    python weight_facts.py "Модуль экспорта в CSV падает с 500 с утра."
"""
import json
import os
import sys
import urllib.request

URL = "https://openrouter.ai/api/alpha/decisions"
MODEL = "typesafe/jev-1.13"  # pin the version; ~typesafe/jev-latest moves

KIND_F = {"факт": 1.0, "процедура": 0.75, "обсуждение": 0.5, "шум": 0.15}

RUBRIC = {
    "reliability": {"type": "noul",
        "instructions": "Утверждение достоверно: подтверждается конкретными данными "
                        "источника, без домыслов, мнений и оговорок?"},
    "importance": {"type": "score",
        "instructions": "Значимость утверждения для базы знаний.",
        "criteria": ["Фон", "Второстепенное", "Важное", "Ключевое"]},
    "specificity": {"type": "score",
        "instructions": "Насколько конкретны данные в утверждении?",
        "criteria": ["Общее", "Частичное", "Конкретное", "Точное"]},
    "kind": {"type": "choice",
        "instructions": "Чем является фрагмент?",
        "criteria": {"факт": "состояние/событие/результат с опорой на данные",
                     "процедура": "поручение, план, организационное",
                     "обсуждение": "мнение, позиция, спор",
                     "шум": "вода, повтор, малосодержательное"}},
}


def weight(reliability: float, kind: str, importance: int, specificity: int) -> float:
    return round(0.50 * reliability + 0.25 * KIND_F.get(kind, 0.5)
                 + 0.15 * importance / 3 + 0.10 * specificity / 3, 3)


def main() -> None:
    claim = " ".join(sys.argv[1:]) or "Экспорт отчёта падает с ошибкой 500 с утра."
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("set OPENROUTER_API_KEY")
    state = f"Источник: оперативная сводка.\nТекст: {claim}"
    req = urllib.request.Request(
        URL,
        data=json.dumps({"model": MODEL, "state": state, "questions": RUBRIC}).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    # macOS system python has no default CA bundle — use the system one if present
    import ssl
    cafile = "/etc/ssl/cert.pem"
    ctx = ssl.create_default_context(cafile=cafile if os.path.exists(cafile) else None)
    with urllib.request.urlopen(req, timeout=90, context=ctx) as r:
        resp = json.load(r)

    a = resp["answers"]
    rel = a["reliability"]["noul"]
    imp = a["importance"]["score"]
    spec = a["specificity"]["score"]
    kind = a["kind"]["choice"]
    w = weight(rel, kind, imp, spec)
    usage = resp.get("usage", {})

    label = "high" if w >= 0.75 else ("medium" if w >= 0.5 else "low")
    print(f"claim      : {claim}")
    print(f"reliability: {rel:.3f}")
    print(f"importance : {imp}/3")
    print(f"specificity: {spec}/3")
    print(f"kind       : {kind}")
    print(f"weight     : {w}  ({label})")
    print(f"cost       : ${usage.get('cost', 0):.6f}  "
          f"({usage.get('input_tokens', '?')} input tokens)")


if __name__ == "__main__":
    main()
