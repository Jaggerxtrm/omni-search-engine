"""
OpenAI Embedding Service

Integrates with OpenAI API to generate embeddings for text chunks.
Implements batch processing and exponential backoff retry logic.
"""

import asyncio

from openai import APIConnectionError, APIError, AsyncOpenAI, RateLimitError


class EmbeddingService:
    """
    Service for generating text embeddings using OpenAI API.

    Features:
    - Batch processing (up to 100 texts per call)
    - Exponential backoff retry logic
    - Error handling and logging
    """

    def __init__(
        self,
        api_key: str,
        model: str = "text-embedding-3-small",
        batch_size: int = 100,
        max_retries: int = 3,
        initial_retry_delay: float = 2.0,
    ):
        """
        Initialize embedding service.

        Args:
            api_key: OpenAI API key
            model: Embedding model to use
            batch_size: Maximum texts per API call
            max_retries: Maximum retry attempts on failure
            initial_retry_delay: Initial delay in seconds for exponential backoff
        """
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model
        self.batch_size = batch_size
        self.max_retries = max_retries
        self.initial_retry_delay = initial_retry_delay

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.

        Processes in batches and includes retry logic for API failures.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors (one per input text)

        Raises:
            OpenAIError: If all retry attempts fail
            ValueError: If texts list is empty
        """
        if not texts:
            raise ValueError("Cannot embed empty list of texts")

        all_embeddings = []

        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            batch_embeddings = await self._embed_batch_with_retry(batch)
            all_embeddings.extend(batch_embeddings)

        return all_embeddings

    async def embed_single(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text string to embed

        Returns:
            Embedding vector

        Raises:
            OpenAIError: If all retry attempts fail
        """
        embeddings = await self.embed_texts([text])
        return embeddings[0]

    async def _embed_batch_with_retry(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a batch of texts with exponential backoff retry logic.

        Args:
            texts: Batch of texts to embed (max batch_size)

        Returns:
            List of embedding vectors

        Raises:
            OpenAIError: If all retry attempts fail
        """
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                return await self._embed_batch(texts)

            except RateLimitError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self.initial_retry_delay * (2**attempt)
                    print(
                        f"Rate limit hit. Retrying in {delay}s... "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(delay)

            except APIConnectionError as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = self.initial_retry_delay * (2**attempt)
                    print(
                        f"Connection error. Retrying in {delay}s... "
                        f"(attempt {attempt + 1}/{self.max_retries})"
                    )
                    await asyncio.sleep(delay)

            except APIError as e:
                last_error = e
                # Don't retry on client errors (4xx), only server errors (5xx)
                status_code = getattr(e, "status_code", None)
                if status_code and 500 <= status_code < 600:
                    if attempt < self.max_retries - 1:
                        delay = self.initial_retry_delay * (2**attempt)
                        print(
                            f"Server error {status_code}. Retrying in {delay}s... "
                            f"(attempt {attempt + 1}/{self.max_retries})"
                        )
                        await asyncio.sleep(delay)
                    else:
                        raise
                else:
                    # Client error, don't retry
                    raise

        # All retries exhausted
        if last_error:
            raise last_error
        else:
            raise RuntimeError("Failed to embed batch after all retries")

    async def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Call OpenAI API to embed a batch of texts (no retry logic).

        Args:
            texts: Batch of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            OpenAIError: On API errors
        """
        # Preprocessing: replace newlines with spaces as recommended by OpenAI for better performance
        processed_texts = [text.replace("\n", " ") for text in texts]
        
        response = await self.client.embeddings.create(input=processed_texts, model=self.model)

        # Extract embeddings in order
        embeddings = [item.embedding for item in response.data]

        return embeddings

    async def get_embedding_dimension(self) -> int:
        """
        Get the dimensionality of embeddings from this model.

        Returns:
            Number of dimensions in embedding vectors

        Raises:
            OpenAIError: If test embedding fails
        """
        # Generate a test embedding to determine dimensions
        test_embedding = await self.embed_single("test")
        return len(test_embedding)


def create_embedding_service(
    api_key: str, model: str = "text-embedding-3-small", batch_size: int = 100
) -> EmbeddingService:
    """
    Convenience function to create an embedding service.

    Args:
        api_key: OpenAI API key
        model: Embedding model to use
        batch_size: Maximum texts per API call

    Returns:
        Configured EmbeddingService instance
    """
    return EmbeddingService(api_key=api_key, model=model, batch_size=batch_size)
