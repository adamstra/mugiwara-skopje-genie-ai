from typing import List, Dict, Any, Optional
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from src.config import DEFAULT_GEN_MODEL, MAX_GENERATIVE_MODEL_CALLS_PER_QUESTION, MAX_GENERATED_TOKENS_PER_QUESTION

class LocalModelRunner:
    """Runs a local generative model under 3B parameters with strict tracking of calls and tokens."""

    def __init__(self, model_id: str = DEFAULT_GEN_MODEL, device: Optional[str] = None):
        self.model_id = model_id
        
        # Determine device (MPS for Apple Silicon, CUDA for Nvidia, CPU fallback)
        if device:
            self.device = device
        elif torch.backends.mps.is_available():
            self.device = "mps"
        elif torch.cuda.is_available():
            self.device = "cuda"
        else:
            self.device = "cpu"

        print(f"[ModelRunner] Loading model '{self.model_id}' on {self.device}...")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id, trust_remote_code=True)
        
        # Load in float16/bfloat16 for fast inference
        dtype = torch.bfloat16 if self.device in ["mps", "cuda"] else torch.float32
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            torch_dtype=dtype,
            device_map=self.device,
            trust_remote_code=True
        )
        self.model.eval()

        # Parameter count verification
        total_params = sum(p.numel() for p in self.model.parameters())
        print(f"[ModelRunner] Total parameters: {total_params:,} ({total_params/1e9:.3f}B)")
        if total_params > 3_000_000_000:
            print(f"[WARNING] Parameter count ({total_params/1e9:.3f}B) exceeds 3.00B parameter limit!")

        # Reset call tracking
        self.call_count = 0
        self.tokens_generated = 0

    def reset_budget(self):
        self.call_count = 0
        self.tokens_generated = 0

    def generate(self, messages: List[Dict[str, str]], max_new_tokens: int = 1024, temperature: float = 0.2) -> str:
        """Generates a response from chat messages, enforcing rules limits."""
        if self.call_count >= MAX_GENERATIVE_MODEL_CALLS_PER_QUESTION:
            raise RuntimeError(f"Exceeded max calls per question ({MAX_GENERATIVE_MODEL_CALLS_PER_QUESTION})")

        prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.device)

        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature if temperature > 0 else None,
                do_sample=temperature > 0,
                pad_token_id=self.tokenizer.eos_token_id
            )

        new_tokens = outputs[0][inputs.input_ids.shape[1]:]
        gen_tokens_count = len(new_tokens)

        self.call_count += 1
        self.tokens_generated += gen_tokens_count

        if self.tokens_generated > MAX_GENERATED_TOKENS_PER_QUESTION:
            raise RuntimeError(f"Exceeded max token limit ({MAX_GENERATED_TOKENS_PER_QUESTION})")

        response = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
        return response.strip()
