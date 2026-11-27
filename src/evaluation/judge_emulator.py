from typing import Dict, Any, List, Optional
import re

class JudgeEmulator:
    """Emulates the competition LLM judge evaluation metric for local cross-validation."""

    @staticmethod
    def calculate_question_score(correctness: float, evidence_support: float) -> float:
        """
        Formula: 0.8 * correctness + 0.2 * correctness * evidence_support
        correctness: 1.0 (correct), 0.5 (partially correct), 0.0 (incorrect)
        evidence_support: 1.0 (complete), 0.5 (incomplete), 0.0 (missing/wrong)
        """
        c = max(0.0, min(1.0, correctness))
        e = max(0.0, min(1.0, evidence_support))
        return 0.8 * c + 0.2 * c * e

    @classmethod
    def evaluate_batch(cls, scores_list: List[Dict[str, float]]) -> Dict[str, float]:
        """
        scores_list: list of dicts with keys 'correctness' and 'evidence_support'
        Returns mean score, mean correctness, and mean evidence credit.
        """
        if not scores_list:
            return {"mean_score": 0.0, "mean_correctness": 0.0, "mean_evidence": 0.0}

        total_scores = []
        c_list = []
        e_list = []

        for item in scores_list:
            c = item.get("correctness", 0.0)
            e = item.get("evidence_support", 0.0)
            score = cls.calculate_question_score(c, e)
            total_scores.append(score)
            c_list.append(c)
            e_list.append(e)

        return {
            "mean_score": sum(total_scores) / len(total_scores),
            "mean_correctness": sum(c_list) / len(c_list),
            "mean_evidence": sum(e_list) / len(e_list),
            "total_questions": len(scores_list)
        }
