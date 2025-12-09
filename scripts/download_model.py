import os
from huggingface_hub import snapshot_download  # type: ignore[import-not-found]

if __name__ == "__main__":
    model_id = os.environ.get("MODEL_ID", "BAAI/bge-large-en-v1.5")
    cache_dir = os.environ.get("CACHE_DIR", "/data")
    revision = os.environ.get("REVISION", "main")
    print(f"Downloading model {model_id} to {cache_dir} with revision {revision}...")
    snapshot_download(repo_id=model_id, cache_dir=cache_dir, revision=revision)  # nosec
    print("Model downloaded successfully!")
