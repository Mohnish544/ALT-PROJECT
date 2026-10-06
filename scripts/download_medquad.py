#!/usr/bin/env python3
"""
Download and Prepare MedQuAD Dataset
======================================
Downloads MedQuAD XML files from the official GitHub repository,
parses Q&A pairs, and saves them as data/medquad/medquad.jsonl.

MedQuAD License: Apache 2.0
Source: https://github.com/abachaa/MedQuAD

Usage:
    python scripts/download_medquad.py [--max-entries N]

Notes:
- Full dataset ~47k Q&A pairs from 12 NIH sources.
- Use --max-entries for a quick demo build (e.g., 2000 entries).
- Network access required on first run; cached after.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Add project root to path so we can import backend config
sys.path.insert(0, str(Path(__file__).parent.parent))

MEDQUAD_REPO = "https://github.com/abachaa/MedQuAD/archive/refs/heads/master.zip"
OUTPUT_DIR = Path("data/medquad")
OUTPUT_FILE = OUTPUT_DIR / "medquad.jsonl"

# MedQuAD NLM source directories within the zip
NLM_SOURCES = [
    "1_CancerGov_QA",
    "2_GARD_QA",
    "3_GHR_QA",
    "4_MedlineplusGov_QA",
    "5_NIDDK_QA",
    "6_NINDS_QA",
    "7_SeniorHealth_QA",
    "8_NHLBI_QA",
    "9_CDC_QA",
    "10_MedicineNet_QA",
    "11_Eunice_QA",
    "12_ClinicalTrials_QA",
]


def parse_xml_file(xml_path: Path) -> list[dict]:
    """Parse a single MedQuAD XML file into Q&A dicts."""
    entries = []
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except ET.ParseError as exc:
        logger.warning("XML parse error in %s: %s", xml_path.name, exc)
        return entries

    # MedQuAD XML structure: <Document> → <QAPairs> → <QAPair>
    focus = root.findtext("Focus") or xml_path.stem
    source = xml_path.parent.name.split("_", 1)[-1] if "_" in xml_path.parent.name else xml_path.parent.name

    for qa_pair in root.findall(".//QAPair"):
        question_el = qa_pair.find("Question")
        answer_el = qa_pair.find("Answer")

        if question_el is None or answer_el is None:
            continue

        question = (question_el.text or "").strip()
        answer = (answer_el.text or "").strip()
        qtype = question_el.get("qtype", "")

        if not question or not answer:
            continue

        entries.append({
            "question": question,
            "answer": answer,
            "source": source,
            "focus": focus,
            "qtype": qtype,
        })

    return entries


def download_and_extract(output_dir: Path) -> Path:
    """Download the MedQuAD GitHub archive and extract it."""
    import io
    import urllib.request
    import zipfile

    zip_path = output_dir / "medquad_master.zip"
    extract_path = output_dir / "MedQuAD-master"

    if extract_path.exists():
        logger.info("Archive already extracted at %s", extract_path)
        return extract_path

    logger.info("Downloading MedQuAD from GitHub (~30 MB)...")
    try:
        with urllib.request.urlopen(MEDQUAD_REPO, timeout=120) as response:
            data = response.read()
    except Exception as exc:
        raise RuntimeError(
            f"Download failed: {exc}\n"
            "Please manually download from https://github.com/abachaa/MedQuAD "
            "and place the extracted folder at data/medquad/MedQuAD-master/"
        )

    zip_path.write_bytes(data)
    logger.info("Download complete (%d MB). Extracting...", len(data) // 1_000_000)

    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        zf.extractall(output_dir)

    logger.info("Extracted to %s", extract_path)
    return extract_path


def build_jsonl(extract_path: Path, output_file: Path, max_entries: int | None = None) -> int:
    """Convert XML files to JSONL, returning total entry count."""
    all_entries: list[dict] = []

    for source_dir_name in NLM_SOURCES:
        source_dir = extract_path / source_dir_name
        if not source_dir.exists():
            logger.warning("Source directory not found: %s", source_dir)
            continue

        xml_files = list(source_dir.glob("*.xml"))
        logger.info("Processing %s: %d XML files", source_dir_name, len(xml_files))

        for xml_file in xml_files:
            entries = parse_xml_file(xml_file)
            all_entries.extend(entries)

            if max_entries and len(all_entries) >= max_entries:
                all_entries = all_entries[:max_entries]
                break

        if max_entries and len(all_entries) >= max_entries:
            break

    # Write JSONL
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        for entry in all_entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    return len(all_entries)


def main():
    parser = argparse.ArgumentParser(description="Download and prepare MedQuAD dataset")
    parser.add_argument(
        "--max-entries", type=int, default=None,
        help="Limit number of entries (for fast demo; default: all ~47k)"
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if OUTPUT_FILE.exists():
        count = sum(1 for _ in open(OUTPUT_FILE))
        logger.info("MedQuAD JSONL already exists: %d entries at %s", count, OUTPUT_FILE)
        if not args.max_entries or count >= args.max_entries:
            logger.info("Nothing to do. Delete %s to re-download.", OUTPUT_FILE)
            return

    try:
        extract_path = download_and_extract(OUTPUT_DIR)
    except RuntimeError as exc:
        logger.error("%s", exc)
        sys.exit(1)

    logger.info("Building JSONL (max_entries=%s)...", args.max_entries or "all")
    count = build_jsonl(extract_path, OUTPUT_FILE, args.max_entries)
    logger.info("Done! Saved %d Q&A pairs to %s", count, OUTPUT_FILE)


if __name__ == "__main__":
    main()
