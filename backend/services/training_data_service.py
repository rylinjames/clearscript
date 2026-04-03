"""
Training Data Collection Service.
Saves corrected contract analysis outputs for future OpenAI fine-tuning.
Each record is a (contract_text, corrected_analysis) pair stored as JSONL.
Once you have 50+ examples, use this file to fine-tune GPT-4o-mini.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

TRAINING_DATA_DIR = Path(__file__).parent.parent / "data" / "training"
TRAINING_DATA_DIR.mkdir(parents=True, exist_ok=True)
TRAINING_FILE = TRAINING_DATA_DIR / "contract_analysis_training.jsonl"


def save_training_example(
    contract_text: str,
    original_analysis: dict,
    corrected_analysis: dict,
    feedback_notes: str = "",
    contract_filename: str = "",
) -> dict:
    """
    Save a corrected contract analysis as a training example.

    Args:
        contract_text: The original contract text that was analyzed
        original_analysis: The AI's original output
        corrected_analysis: The human-corrected output
        feedback_notes: Optional notes about what was wrong
        contract_filename: Original filename for reference

    Returns:
        Dict with save status and example count
    """
    # Format as OpenAI fine-tuning JSONL
    # See: https://platform.openai.com/docs/guides/fine-tuning
    training_example = {
        "messages": [
            {
                "role": "system",
                "content": "You are a PBM contract analyst advising employer health plan sponsors. Analyze the contract and return structured JSON rating each provision as employer_favorable, neutral, or pbm_favorable."
            },
            {
                "role": "user",
                "content": f"Analyze this PBM contract:\n\n{contract_text[:12000]}"
            },
            {
                "role": "assistant",
                "content": json.dumps(corrected_analysis, default=str)
            }
        ],
        # Metadata (not used in fine-tuning but useful for tracking)
        "_metadata": {
            "timestamp": datetime.now().isoformat(),
            "contract_filename": contract_filename,
            "feedback_notes": feedback_notes,
            "had_corrections": original_analysis != corrected_analysis,
        }
    }

    # Append to JSONL file
    with open(TRAINING_FILE, "a") as f:
        f.write(json.dumps(training_example, default=str) + "\n")

    # Count total examples
    count = sum(1 for _ in open(TRAINING_FILE)) if TRAINING_FILE.exists() else 0

    logger.info(f"Saved training example #{count} from {contract_filename}")

    return {
        "status": "saved",
        "total_examples": count,
        "ready_for_finetuning": count >= 50,
        "message": f"Training example saved. {count}/50 examples collected." + (
            " Ready for fine-tuning!" if count >= 50 else f" Need {50 - count} more."
        ),
    }


def get_training_stats() -> dict:
    """Get stats about collected training data."""
    if not TRAINING_FILE.exists():
        return {"total_examples": 0, "ready_for_finetuning": False}

    count = sum(1 for _ in open(TRAINING_FILE))
    return {
        "total_examples": count,
        "ready_for_finetuning": count >= 50,
        "file_path": str(TRAINING_FILE),
        "file_size_kb": round(TRAINING_FILE.stat().st_size / 1024, 1),
    }


def export_for_finetuning() -> str:
    """
    Export training data in OpenAI fine-tuning format.
    Strips metadata fields, returns clean JSONL.
    """
    if not TRAINING_FILE.exists():
        return ""

    clean_lines = []
    with open(TRAINING_FILE) as f:
        for line in f:
            example = json.loads(line)
            # Remove metadata, keep only messages
            clean = {"messages": example["messages"]}
            clean_lines.append(json.dumps(clean))

    output_file = TRAINING_DATA_DIR / "finetuning_ready.jsonl"
    with open(output_file, "w") as f:
        f.write("\n".join(clean_lines))

    return str(output_file)
