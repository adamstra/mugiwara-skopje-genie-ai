from pathlib import Path
from typing import List, Dict, Any, Union
import re

class SubmissionGenerator:
    """Generates the official Submission.md format matching StarterNotebook.ipynb exactly."""

    @staticmethod
    def save_submission(
        predictions: Dict[str, Dict[str, Any]],
        expected_ids: List[str],
        output_path: Union[str, Path]
    ) -> Path:
        """
        predictions: dict mapping test_id -> {
            "answer": str,
            "evidence": List[str]  # e.g. ["SRC_... | locator | supported claim"]
        }
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if set(predictions.keys()) != set(expected_ids):
            missing = set(expected_ids) - set(predictions.keys())
            extra = set(predictions.keys()) - set(expected_ids)
            raise ValueError(
                f"Prediction IDs mismatch! Missing: {len(missing)}, Extra: {len(extra)}. "
                f"Expected exactly {len(expected_ids)}."
            )

        chunks = ["# Submission\n"]
        for qid in expected_ids:
            item = predictions[qid]
            answer = item["answer"].strip()
            
            assert answer and not re.search(r"^## ", answer, re.M), f"Invalid answer section for {qid}"
            
            evidence_list = item.get("evidence", [])
            if isinstance(evidence_list, str):
                evidence_list = [evidence_list]
            
            assert isinstance(evidence_list, list), f"Evidence for {qid} must be a list"
            assert all(isinstance(e, str) and "\n" not in e and "\r" not in e for e in evidence_list), \
                f"Evidence items for {qid} must be single-line strings"

            # Construct clean block
            evidence_text = "\n".join("- " + e.strip() for e in evidence_list) if evidence_list else "- Incomplete evidence"
            chunks.append(f"\n## {qid}\n\n{answer}\n\n### Evidence\n{evidence_text}\n")

        text = "".join(chunks)
        assert re.findall(r"^## (.+)$", text, re.M) == expected_ids, "Header structure assertion failed!"
        
        output_path.write_text(text, encoding="utf-8")
        return output_path
