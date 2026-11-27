from typing import Dict, Any, List, Tuple, Optional
import re
from src.agent.prompt_templates import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE
from src.agent.model_runner import LocalModelRunner
from src.index.hybrid_retriever import HybridRetriever

class AnswerEngine:
    """Orchestrates retrieval, prompt construction, model generation, and output parsing."""

    def __init__(self, model_runner: LocalModelRunner, retriever: HybridRetriever):
        self.runner = model_runner
        self.retriever = retriever

    def answer_question(
        self,
        question_id: str,
        question: str,
        context: str = "",
        source_references: str = "",
        top_k: int = 4
    ) -> Tuple[str, str]:
        """
        Processes a question and returns (answer, evidence).
        """
        self.runner.reset_budget()

        # Parse source references to filter retrieval if possible
        source_filter = [s.strip() for s in source_references.split(",") if s.strip()] if source_references else None

        # Retrieve relevant passages
        retrieved_docs = self.retriever.retrieve(
            query=f"{question} {context}",
            top_k=top_k,
            source_filter=source_filter
        )

        evidence_blocks = []
        for i, r in enumerate(retrieved_docs):
            doc = r["document"]
            source = doc.get("source_id", "Unknown")
            fname = doc.get("filename", "")
            page = doc.get("page")
            page_info = f" (Page {page})" if page else ""
            txt = doc.get("text", "")[:1200]  # truncate individual chunks to keep prompt clean
            evidence_blocks.append(f"[{i+1}] Source: {source} / {fname}{page_info}\nContent: {txt}\n")

        retrieved_evidence_text = "\n".join(evidence_blocks) if evidence_blocks else "No matching evidence found in indexed sources."

        # Construct prompt
        user_content = USER_PROMPT_TEMPLATE.format(
            context=context or "N/A",
            question=question,
            source_references=source_references or "N/A",
            retrieved_evidence=retrieved_evidence_text
        )

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content}
        ]

        raw_output = self.runner.generate(messages, max_new_tokens=800, temperature=0.1)

        # Parse into Answer and Evidence
        answer, evidence = self._parse_output(raw_output, retrieved_docs)
        return answer, evidence

    def _parse_output(self, output: str, retrieved_docs: List[Dict[str, Any]]) -> Tuple[str, str]:
        """Splits output into Answer and Evidence sections."""
        answer = ""
        evidence = ""

        # Look for explicit "Answer:" and "Evidence:" tags
        ans_match = re.search(r"Answer:\s*(.*?)(?=Evidence:|$)", output, re.DOTALL | re.IGNORECASE)
        evi_match = re.search(r"Evidence:\s*(.*)", output, re.DOTALL | re.IGNORECASE)

        if ans_match:
            answer = ans_match.group(1).strip()
        if evi_match:
            evidence = evi_match.group(1).strip()

        # Fallback if structure was slightly broken
        if not answer:
            answer = output.strip()

        if not evidence:
            # Construct default evidence from top retrieved docs
            citations = []
            for r in retrieved_docs[:3]:
                d = r["document"]
                s = d.get("source_id", d.get("filename", "Source"))
                p = d.get("page")
                citations.append(f"{s}" + (f", Page {p}" if p else ""))
            evidence = "; ".join(citations) if citations else "No explicit source reference provided."

        return answer, evidence
