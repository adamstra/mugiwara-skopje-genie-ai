from pathlib import Path
from typing import List, Dict, Any, Tuple
import re

class SubmissionValidator:
    """Validates the markdown submission file to guarantee 100% compliance with Zindi parser."""

    @staticmethod
    def validate(submission_path: Path, expected_ids: List[str]) -> Tuple[bool, List[str]]:
        errors = []
        warnings = []
        submission_path = Path(submission_path)

        if not submission_path.exists():
            return False, [f"Submission file does not exist: {submission_path}"]

        content = submission_path.read_text(encoding="utf-8")

        # 1. Check title
        if not content.startswith("# Submission"):
            warnings.append("Submission does not start with '# Submission' header.")

        # 2. Extract ## <ID> headers
        found_ids = re.findall(r"^##\s+([^\n]+)$", content, re.MULTILINE)
        
        # Check order and exact match
        if found_ids != expected_ids:
            if len(found_ids) != len(expected_ids):
                errors.append(f"Expected {len(expected_ids)} questions, but found {len(found_ids)} in submission.")
            
            missing = set(expected_ids) - set(found_ids)
            if missing:
                errors.append(f"Missing {len(missing)} IDs (e.g. {list(missing)[:5]})")
            
            extra = set(found_ids) - set(expected_ids)
            if extra:
                errors.append(f"Found {len(extra)} unexpected IDs (e.g. {list(extra)[:5]})")
            
            if len(found_ids) == len(expected_ids) and set(found_ids) == set(expected_ids):
                errors.append("IDs are not in the exact expected order.")

        # 3. Parse blocks and validate answer + evidence
        blocks = re.findall(r"^##\s+([^\n]+)\n\n(.*?)(?=\n##\s+|\Z)", content, re.DOTALL | re.MULTILINE)
        
        for qid, body in blocks:
            clean_qid = qid.strip()
            
            # Split body into Answer and ### Evidence
            parts = re.split(r"\n###\s*Evidence\s*\n", body, maxsplit=1)
            answer_text = parts[0].strip() if len(parts) > 0 else ""
            evidence_text = parts[1].strip() if len(parts) > 1 else ""

            if not answer_text or answer_text.lower() in ["", "write your answer here.", "todo", "n/a", "none"]:
                errors.append(f"Question {clean_qid} has placeholder or empty answer.")

            if not evidence_text or evidence_text.lower() in ["", "- source_id | locator | supported claim"]:
                warnings.append(f"Question {clean_qid} has placeholder or missing evidence.")

        is_valid = len(errors) == 0
        all_messages = errors + [f"[WARNING] {w}" for w in warnings]
        return is_valid, all_messages
