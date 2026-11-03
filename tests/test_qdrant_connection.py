from app.services.vector_store import QdrantVectorStore

store = QdrantVectorStore()

store.create_collection()

print("Collection created or already exists.")

print(
    "Collection exists:",
    store.client.collection_exists("document_chunks")
)