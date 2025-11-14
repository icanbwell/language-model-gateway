# Stage 1: Download models
FROM ghcr.io/open-webui/open-webui:v0.6.34-slim AS model-downloader

RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*
RUN pip install sentence-transformers==5.1.1 faster-whisper tiktoken

RUN python -c "import os; from sentence_transformers import SentenceTransformer; SentenceTransformer(os.environ['RAG_EMBEDDING_MODEL'], device='cpu')" && \
    python -c "import os; from faster_whisper import WhisperModel; WhisperModel(os.environ['WHISPER_MODEL'], device='cpu', compute_type='int8', download_root=os.environ['WHISPER_MODEL_DIR'])" && \
    python -c "import os; import tiktoken; tiktoken.get_encoding(os.environ['TIKTOKEN_ENCODING_NAME'])";

# Stage 2: Final image
FROM ghcr.io/open-webui/open-webui:v0.6.34-slim

RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*
RUN pip install sentence-transformers==5.1.1 faster-whisper tiktoken

# Copy models and cache folders from the builder stage
COPY --from=model-downloader /app/backend/data/cache/embedding/models /app/backend/data/cache/embedding/models
COPY --from=model-downloader /app/backend/data/cache/whisper/models /app/backend/data/cache/whisper/models
COPY --from=model-downloader /app/backend/data/cache/tiktoken /app/backend/data/cache/tiktoken

RUN ls -halt /app/backend/data/cache/embedding/models && \
    ls -halt /app/backend/data/cache/whisper/models && \
    ls -halt /app/backend/data/cache/tiktoken