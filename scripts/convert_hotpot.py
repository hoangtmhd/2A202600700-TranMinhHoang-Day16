"""Convert HotpotQA dev distractor set to QAExample format and sample 150 records."""
import json
from pathlib import Path

SRC = Path("data/hotpot_dev_distractor_v1.json")
DST = Path("data/hotpot_150.json")
N = 150

raw = json.loads(SRC.read_text(encoding="utf-8"))
print(f"Total records in source: {len(raw)}")

DIFFICULTY_MAP = {"easy": "easy", "medium": "medium", "hard": "hard"}

samples = []
for item in raw[:N]:
    # context is list of [title, list_of_sentences]
    ctx = [
        {"title": title, "text": " ".join(sentences)}
        for title, sentences in item["context"]
    ]
    samples.append({
        "qid": item["_id"],
        "difficulty": DIFFICULTY_MAP.get(item["level"], "medium"),
        "question": item["question"],
        "gold_answer": item["answer"],
        "context": ctx,
    })

DST.write_text(json.dumps(samples, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Saved {len(samples)} samples to {DST}")
