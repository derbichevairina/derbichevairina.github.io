#!/usr/bin/env python3
"""Convert YAML questions to JavaScript data file."""

import json
from pathlib import Path

import yaml


def load_yaml_questions(yaml_path: Path) -> list[dict]:
    """Load questions from YAML file."""
    with open(yaml_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("questions", [])


def convert_to_cards(questions: list[dict], start_id: int = 1) -> list[dict]:
    """Convert questions to card format."""
    cards = []
    for i, q in enumerate(questions):
        cards.append({
            "id": start_id + i,
            "question": q["question"],
            "answer": q["answer"],
            "category": q.get("category", "General"),
        })
    return cards


def generate_js_file(cards: list[dict], output_path: Path) -> None:
    """Generate JavaScript data file."""
    js_content = f"// Auto-generated from YAML files. Do not edit manually.\n"
    js_content += f"// Generated cards: {len(cards)}\n\n"
    js_content += f"const CARDS = {json.dumps(cards, ensure_ascii=False, indent=2)};\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(js_content)

    print(f"Generated {output_path} with {len(cards)} cards")


def main() -> None:
    """Main entry point."""
    base_dir = Path(__file__).parent.parent
    questions_dir = base_dir / "questions"
    output_path = Path(__file__).parent / "data.js"

    all_cards: list[dict] = []

    yaml_files = sorted(questions_dir.glob("*.yaml"))

    for yaml_file in yaml_files:
        print(f"Loading {yaml_file.name}...")
        questions = load_yaml_questions(yaml_file)
        cards = convert_to_cards(questions, start_id=len(all_cards) + 1)
        all_cards.extend(cards)

    generate_js_file(all_cards, output_path)

    categories = {}
    for card in all_cards:
        cat = card["category"]
        categories[cat] = categories.get(cat, 0) + 1

    print("\nCategories:")
    for cat, count in sorted(categories.items()):
        print(f"  - {cat}: {count}")


if __name__ == "__main__":
    main()
