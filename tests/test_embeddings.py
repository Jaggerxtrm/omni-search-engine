#!/usr/bin/env python3
"""
Test embeddings service with OpenAI API.
"""

import os
from embeddings import EmbeddingService

# Get API key from environment
api_key = os.getenv('OPENAI_API_KEY')
if not api_key:
    print("Error: OPENAI_API_KEY environment variable not set")
    exit(1)

print("Testing EmbeddingService")
print("=" * 80)

# Initialize service
service = EmbeddingService(
    api_key=api_key,
    model="text-embedding-3-small",
    batch_size=100
)

print(f"✓ Service initialized with model: {service.model}")
print()

# Test 1: Single embedding
print("Test 1: Single text embedding")
print("-" * 80)
text = "Gold is a precious metal used as a store of value."
print(f"Input: {text}")

embedding = service.embed_single(text)
print(f"✓ Generated embedding with {len(embedding)} dimensions")
print(f"  First 5 values: {embedding[:5]}")
print()

# Test 2: Batch embedding
print("Test 2: Batch embedding")
print("-" * 80)
texts = [
    "Treasury bonds are government securities.",
    "The Federal Reserve sets interest rates.",
    "Gold prices correlate with real interest rates.",
    "Oil is a key commodity in global markets.",
    "Equity markets reflect investor sentiment."
]
print(f"Input: {len(texts)} texts")

embeddings = service.embed_texts(texts)
print(f"✓ Generated {len(embeddings)} embeddings")

for i, emb in enumerate(embeddings):
    print(f"  Text {i+1}: {len(emb)} dimensions, first 3 values: {emb[:3]}")
print()

# Test 3: Get embedding dimension
print("Test 3: Get embedding dimension")
print("-" * 80)
dimension = service.get_embedding_dimension()
print(f"✓ Embedding dimension: {dimension}")
print()

# Validation
print("=" * 80)
print("VALIDATION:")

if dimension == 1536:
    print(f"  ✓ Correct dimension for text-embedding-3-small (1536)")
else:
    print(f"  ✗ Unexpected dimension: {dimension} (expected 1536)")

if len(embeddings) == len(texts):
    print(f"  ✓ Batch size matches: {len(embeddings)} embeddings for {len(texts)} texts")
else:
    print(f"  ✗ Batch size mismatch: {len(embeddings)} != {len(texts)}")

if all(len(emb) == dimension for emb in embeddings):
    print(f"  ✓ All embeddings have consistent dimension")
else:
    print(f"  ✗ Inconsistent embedding dimensions")

print()
print("✓ All tests passed!")
