import argparse
import os

import numpy as np

# Try to import turbovec; gracefully handle if it's not installed yet.
try:
    from turbovec import IdMapIndex
except ImportError:
    print("WARNING: turbovec is not installed. Please run: pip install turbovec")
    IdMapIndex = None

MEMORY_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "brain")
MEMORY_FILE = os.path.join(MEMORY_DIR, "global_memory.tvim")

class GlobalMemoryEngine:
    def __init__(self, dim=1536, bit_width=4):
        self.dim = dim
        self.bit_width = bit_width
        self.index = None

        if IdMapIndex is None:
            return

        os.makedirs(MEMORY_DIR, exist_ok=True)
        self.load_or_create()

    def load_or_create(self):
        if os.path.exists(MEMORY_FILE):
            print(f"Loading AI memory from {MEMORY_FILE}...")
            self.index = IdMapIndex.load(MEMORY_FILE)
        else:
            print("Initializing new AI memory index (Turbovec)...")
            self.index = IdMapIndex(dim=self.dim, bit_width=self.bit_width)

    def add_memories(self, vectors, ids):
        """
        Add new embeddings to memory.
        :param vectors: 2D numpy array of float32, shape (N, dim)
        :param ids: 1D numpy array of uint64, shape (N,)
        """
        if self.index is None:
            raise RuntimeError("turbovec index is not initialized.")

        assert vectors.shape[1] == self.dim, f"Vectors must have dimension {self.dim}"
        assert len(vectors) == len(ids), "Vectors and ids must have the same length"

        self.index.add_with_ids(vectors, ids)
        self.save()
        print(f"Added {len(ids)} new memories.")

    def search_memory(self, query_vector, k=5, allowlist=None):
        """
        Search for the top k most relevant memories.
        :param query_vector: 2D numpy array of float32, shape (N_queries, dim)
        :param k: number of results to return per query
        :param allowlist: optional 1D numpy array of uint64 for hybrid filtering
        :return: (scores, ids)
        """
        if self.index is None:
            raise RuntimeError("turbovec index is not initialized.")

        if allowlist is not None:
            return self.index.search(query_vector, k=k, allowlist=allowlist)
        return self.index.search(query_vector, k=k)

    def remove_memory(self, memory_id):
        if self.index is None:
            raise RuntimeError("turbovec index is not initialized.")
        self.index.remove(memory_id)
        self.save()
        print(f"Removed memory id {memory_id}.")

    def save(self):
        if self.index is not None:
            self.index.write(MEMORY_FILE)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Global AI Memory Engine (Turbovec)")
    parser.add_argument("--status", action="store_true", help="Check memory engine status")
    parser.add_argument("--test", action="store_true", help="Run a quick sanity check")
    args = parser.parse_args()

    if IdMapIndex is None:
        print("Cannot run engine without turbovec.")
        exit(1)

    engine = GlobalMemoryEngine()

    if args.status:
        print("Memory engine is online and ready.")

    if args.test:
        print("Running sanity test...")
        dummy_vectors = np.random.randn(10, 1536).astype(np.float32)
        # Normalize vectors for cosine similarity equivalent
        dummy_vectors = dummy_vectors / np.linalg.norm(dummy_vectors, axis=1, keepdims=True)
        dummy_ids = np.array([100 + i for i in range(10)], dtype=np.uint64)

        engine.add_memories(dummy_vectors, dummy_ids)

        query = dummy_vectors[0:1] # Search for the exact first dummy vector
        scores, ids = engine.search_memory(query, k=3)
        print(f"Search results for dummy query:\n IDs: {ids}\n Scores: {scores}")
        print("Test complete.")
