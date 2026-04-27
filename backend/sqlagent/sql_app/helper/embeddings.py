from sentence_transformers import SentenceTransformer

# Load model once (important for performance)
model = SentenceTransformer("all-MiniLM-L6-v2")


def embed_text(text: str):
    return model.encode(text).tolist()