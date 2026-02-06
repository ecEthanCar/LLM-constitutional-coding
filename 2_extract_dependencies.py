# -*- coding: utf-8 -*-
"""
Improved dependency extractor for constitutional question sets.
This script now reads the pre-parsed dependency
dictionary from the organized JSON file.
Produces question_dependencies_{organized_stem}.json and .csv
"""

import json
import re
import csv
from pathlib import Path
from typing import Dict, Any, List

def extract_dependencies(json_path: str, output_dir: str = ".") -> None:
    path = Path(json_path)
    if not path.exists():
        raise FileNotFoundError(f"Could not find file: {json_path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunks = data.get("chunks", {})
    all_questions = {}
    for chunk_data in chunks.values():
        for q in chunk_data.get("questions", []):
            all_questions[q["id"]] = q

    known_ids = set(all_questions.keys())
    known_codes = {q["code"] for q in all_questions.values() if q.get("code")}
    all_known_identifiers = known_ids.union(known_codes)
    
    dependency_map: List[Dict[str, Any]] = []

    for qid, qdata in all_questions.items():
        # --- START OF CHANGE ---
        # The conditional field is now a dictionary
        parsed = qdata.get("conditional", {})
        
        # Skip if there's no raw text, meaning it's not a conditional q
        if not parsed.get("raw"):
            continue

        # Directly read the pre-parsed data
        depends_on = parsed.get("depends_on", [])
        # Check dependencies against *all* known IDs and Codes
        missing = [d for d in depends_on if d not in all_known_identifiers]

        dependency_map.append({
            "question_id": qid,
            "question_code": qdata.get("code") or None,
            "conditional_raw": parsed.get("raw", ""),
            "condition_expression": parsed.get("condition_expression", ""),
            "depends_on": depends_on,
            "missing_dependencies": missing,
            "chunk": qdata.get("category"),
            "question_text": qdata.get("question", "")
        })
        # --- END OF CHANGE ---

    if not dependency_map:
        print("No conditional questions found.")
        return

    out_json = Path(output_dir) / f"question_dependencies_{path.stem}.json"
    out_csv = out_json.with_suffix(".csv")

    with open(out_json, "w", encoding="utf-8") as f:
        json.dump(dependency_map, f, indent=2, ensure_ascii=False)

    # write CSV for easy inspection (flatten depends_on)
    with open(out_csv, "w", encoding="utf-8", newline="") as f:
        fieldnames = ["question_id", "question_code", "condition_expression", "depends_on", "missing_dependencies", "chunk", "question_text"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for item in dependency_map:
            writer.writerow({
                "question_id": item["question_id"],
                "question_code": item["question_code"],
                "condition_expression": item["condition_expression"],
                "depends_on": ";".join(item["depends_on"]),
                "missing_dependencies": ";".join(item["missing_dependencies"]),
                "chunk": item["chunk"] or "",
                "question_text": item["question_text"][:200]
            })

    print(f"Saved: {out_json} and {out_csv}")
    print(f"Found {len(dependency_map)} conditional questions.")


if __name__ == "__main__":
    # Replace with your organized JSON filename
    extract_dependencies("organized_constitutional_questions.json", output_dir="extract_dependencies")