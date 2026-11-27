from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
SOURCES_DIR = DATA_DIR / "sources"
OUTPUT_DIR = BASE_DIR / "outputs"
DOCS_DIR = BASE_DIR / "docs"

# Create necessary directories
for directory in [DATA_DIR, SOURCES_DIR, OUTPUT_DIR, DOCS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# Official Competition Constraints
MAX_GENERATIVE_MODEL_CALLS_PER_QUESTION = 15
MAX_GENERATED_TOKENS_PER_QUESTION = 12000
MAX_PARAM_LIMIT = 3_000_000_000  # 3 Billion parameters strictly

# Candidate Generative Models (<= 3B parameters)
# Note: Quantization does NOT reduce parameter count.
CANDIDATE_MODELS = {
    # Strictly < 3.00B (100% compliant guarantee):
    "gemma-2-2b": "google/gemma-2-2b-it",             # 2.61B parameters
    "smollm2-1.7b": "HuggingFaceTB/SmolLM2-1.7B-Instruct", # 1.71B parameters
    "qwen-1.5b": "Qwen/Qwen2.5-1.5B-Instruct",        # 1.54B parameters
    "llama-3.2-1b": "meta-llama/Llama-3.2-1B-Instruct",# 1.24B parameters
    
    # Borderline 3B class (3.08B actual due to vocabulary size):
    "qwen-3b": "Qwen/Qwen2.5-3B-Instruct",            # 3.085B parameters
}

# Default generative model to start with
DEFAULT_GEN_MODEL = "google/gemma-2-2b-it"

# Embedding model for dense retrieval (non-generative, 33M params)
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"

# Target Domains
DOMAINS = {
    "pristina": "Modernizing Transit Route Reviews (Pristina, Kosovo)",
    "rivne": "Unlocking Energy Efficiency Investments (Rivne, Ukraine)",
    "skopje": "Safeguarding Green Infrastructure (Skopje, North Macedonia)",
}
