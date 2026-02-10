"""
@file vision_embedding.py
@module agents/browser/vision_embedding
@layer Layer 4, Layer 5
@component CLIP to Poincare Projection
@version 1.0.0

Converts visual observations to Poincare ball embeddings for geometric containment.
Uses CLIP for vision encoding, then projects to hyperbolic space.
"""

from __future__ import annotations

import hashlib
import logging
import math
from dataclasses import dataclass, field
from io import BytesIO
from typing import List, Optional, Tuple, Union

import numpy as np

logger = logging.getLogger(__name__)

# Numerical stability constant
EPSILON = 1e-10


@dataclass
class EmbeddingResult:
    """Result of embedding an observation."""
    euclidean_embedding: np.ndarray
    poincare_embedding: np.ndarray
    euclidean_norm: float
    poincare_radius: float
    embedding_hash: str
    source: str


@dataclass
class VisionEmbedder:
    """
    Vision embedding system with CLIP and Poincare projection.

    Pipeline:
    1. Image/Screenshot -> CLIP encoding (512D or 768D depending on model)
    2. CLIP embedding -> Linear projection to target dimension
    3. Projected embedding -> Poincare ball projection

    The Poincare projection uses the exponential map to transform
    Euclidean vectors into hyperbolic space while preserving relative
    distances and adding geometric containment properties.

    Attributes:
        target_dim: Target embedding dimension (default 16)
        clip_model: CLIP model name
        projection_matrix: Learned projection from CLIP dim to target dim
    """
    target_dim: int = 16
    clip_model_name: str = "ViT-B/32"
    curvature: float = 1.0  # Poincare ball curvature

    _model: object = None
    _preprocess: object = None
    _projection_matrix: Optional[np.ndarray] = None
    _is_initialized: bool = False
    _device: str = "cpu"

    # Cache for repeated embeddings
    _cache: dict = field(default_factory=dict)
    _cache_max_size: int = 100

    def __post_init__(self):
        """Initialize the embedder state."""
        self._cache = {}

    def _compute_hash(self, data: bytes) -> str:
        """Compute hash of input data for caching."""
        return hashlib.sha256(data).hexdigest()[:16]

    async def initialize(self, device: Optional[str] = None):
        """
        Initialize CLIP model and projection matrix.

        Args:
            device: Device to use ('cpu', 'cuda', 'mps')
        """
        if self._is_initialized:
            return

        try:
            import torch
            import clip
        except ImportError:
            logger.warning(
                "CLIP not installed. Using random projection fallback. "
                "Install with: pip install git+https://github.com/openai/CLIP.git"
            )
            self._initialize_fallback()
            return

        # Determine device
        if device is None:
            if torch.cuda.is_available():
                device = "cuda"
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                device = "mps"
            else:
                device = "cpu"

        self._device = device

        try:
            self._model, self._preprocess = clip.load(self.clip_model_name, device=device)
            clip_dim = self._model.visual.output_dim

            # Initialize projection matrix (random orthogonal for now)
            # In production, this would be learned from data
            self._projection_matrix = self._create_projection_matrix(clip_dim)

            self._is_initialized = True
            logger.info(f"Vision embedder initialized with CLIP {self.clip_model_name} on {device}")
        except Exception as e:
            logger.warning(f"Failed to load CLIP: {e}. Using fallback.")
            self._initialize_fallback()

    def _initialize_fallback(self):
        """Initialize with random projection fallback (no CLIP)."""
        # Use a deterministic random seed for reproducibility
        np.random.seed(42)
        fallback_input_dim = 512  # Simulated CLIP dimension
        self._projection_matrix = self._create_projection_matrix(fallback_input_dim)
        self._is_initialized = True
        logger.info("Vision embedder initialized with fallback (no CLIP)")

    def _create_projection_matrix(self, input_dim: int) -> np.ndarray:
        """
        Create a projection matrix from input_dim to target_dim.

        Uses orthogonal initialization for better gradient properties.

        Args:
            input_dim: Input dimension (CLIP embedding size)

        Returns:
            Projection matrix of shape (input_dim, target_dim)
        """
        # Create random matrix
        matrix = np.random.randn(input_dim, self.target_dim)

        # Orthogonalize using QR decomposition
        q, r = np.linalg.qr(matrix)

        # Ensure correct shape (may need to transpose if input_dim < target_dim)
        if input_dim >= self.target_dim:
            projection = q[:, :self.target_dim]
        else:
            projection = q

        return projection.astype(np.float32)

    def project_to_poincare(self, v: np.ndarray) -> np.ndarray:
        """
        Project Euclidean vector to Poincare ball.

        Uses the exponential map at the origin:
        exp_0(v) = tanh(||v||/2) * v/||v||

        This maps the entire Euclidean space into the open unit ball,
        with the origin mapping to itself and distant points mapping
        close to the boundary.

        Args:
            v: Euclidean vector

        Returns:
            Point in Poincare ball (norm < 1)
        """
        norm = np.linalg.norm(v)

        if norm < EPSILON:
            return v  # Origin maps to origin

        # Exponential map at origin: tanh(||v||/2) * v/||v||
        # The factor of 2 comes from the standard Poincare ball metric
        scale = math.tanh(norm / 2.0)

        result = (scale / norm) * v

        # Ensure we stay strictly inside the ball
        result_norm = np.linalg.norm(result)
        if result_norm >= 1.0 - EPSILON:
            result = result * (1.0 - EPSILON) / result_norm

        return result

    def project_to_poincare_scaled(
        self,
        v: np.ndarray,
        temperature: float = 1.0
    ) -> np.ndarray:
        """
        Project to Poincare ball with temperature scaling.

        Higher temperature = points spread closer to boundary
        Lower temperature = points cluster near origin

        Args:
            v: Euclidean vector
            temperature: Scaling factor (default 1.0)

        Returns:
            Point in Poincare ball
        """
        norm = np.linalg.norm(v)

        if norm < EPSILON:
            return v

        # Scale the norm by temperature before tanh
        scaled_norm = norm * temperature
        scale = math.tanh(scaled_norm / 2.0)

        result = (scale / norm) * v

        result_norm = np.linalg.norm(result)
        if result_norm >= 1.0 - EPSILON:
            result = result * (1.0 - EPSILON) / result_norm

        return result

    async def embed_image(
        self,
        image_data: bytes,
        source: str = "unknown"
    ) -> EmbeddingResult:
        """
        Embed an image into the Poincare ball.

        Pipeline:
        1. Decode image
        2. CLIP encoding
        3. Project to target dimension
        4. Project to Poincare ball

        Args:
            image_data: Raw image bytes (PNG, JPEG, etc.)
            source: Source identifier for logging

        Returns:
            EmbeddingResult with both Euclidean and Poincare embeddings
        """
        if not self._is_initialized:
            await self.initialize()

        # Check cache
        data_hash = self._compute_hash(image_data)
        if data_hash in self._cache:
            logger.debug(f"Cache hit for image {data_hash}")
            return self._cache[data_hash]

        # Get CLIP embedding (or fallback)
        clip_embedding = await self._get_clip_embedding(image_data)

        # Project to target dimension
        euclidean_embedding = np.dot(clip_embedding, self._projection_matrix)

        # Normalize for consistent scale before Poincare projection
        euclidean_norm = np.linalg.norm(euclidean_embedding)
        if euclidean_norm > EPSILON:
            euclidean_embedding = euclidean_embedding / euclidean_norm

        # Project to Poincare ball
        poincare_embedding = self.project_to_poincare(euclidean_embedding)
        poincare_radius = float(np.linalg.norm(poincare_embedding))

        result = EmbeddingResult(
            euclidean_embedding=euclidean_embedding,
            poincare_embedding=poincare_embedding,
            euclidean_norm=euclidean_norm,
            poincare_radius=poincare_radius,
            embedding_hash=data_hash,
            source=source
        )

        # Update cache
        if len(self._cache) >= self._cache_max_size:
            # Remove oldest entry
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[data_hash] = result

        return result

    async def _get_clip_embedding(self, image_data: bytes) -> np.ndarray:
        """
        Get CLIP embedding for image data.

        Args:
            image_data: Raw image bytes

        Returns:
            CLIP embedding as numpy array
        """
        if self._model is None:
            # Fallback: generate deterministic pseudo-embedding from image hash
            return self._fallback_embedding(image_data)

        try:
            import torch
            from PIL import Image

            # Load image
            image = Image.open(BytesIO(image_data)).convert("RGB")

            # Preprocess
            image_input = self._preprocess(image).unsqueeze(0).to(self._device)

            # Encode
            with torch.no_grad():
                features = self._model.encode_image(image_input)

            # Convert to numpy
            embedding = features.cpu().numpy().flatten()

            return embedding.astype(np.float32)

        except Exception as e:
            logger.warning(f"CLIP encoding failed: {e}. Using fallback.")
            return self._fallback_embedding(image_data)

    def _fallback_embedding(self, image_data: bytes) -> np.ndarray:
        """
        Generate deterministic fallback embedding from image hash.

        This is used when CLIP is not available. It creates a consistent
        embedding based on the image content hash.

        Args:
            image_data: Raw image bytes

        Returns:
            Pseudo-embedding array
        """
        # Use SHA-256 to generate deterministic values
        h = hashlib.sha256(image_data).digest()

        # Expand hash to full dimension using SHAKE-256
        import hashlib as hl
        shake = hl.shake_256(image_data)
        expanded = shake.digest(self._projection_matrix.shape[0] * 4)

        # Convert to float array
        embedding = np.frombuffer(expanded, dtype=np.float32)

        # Normalize
        embedding = embedding / (np.linalg.norm(embedding) + EPSILON)

        return embedding

    async def embed_text(
        self,
        text: str,
        source: str = "text"
    ) -> EmbeddingResult:
        """
        Embed text into the Poincare ball using CLIP.

        Args:
            text: Text to embed
            source: Source identifier

        Returns:
            EmbeddingResult with embeddings
        """
        if not self._is_initialized:
            await self.initialize()

        # Check cache
        text_hash = self._compute_hash(text.encode('utf-8'))
        if text_hash in self._cache:
            return self._cache[text_hash]

        # Get CLIP text embedding
        text_embedding = await self._get_text_embedding(text)

        # Project to target dimension
        euclidean_embedding = np.dot(text_embedding, self._projection_matrix)

        # Normalize
        euclidean_norm = np.linalg.norm(euclidean_embedding)
        if euclidean_norm > EPSILON:
            euclidean_embedding = euclidean_embedding / euclidean_norm

        # Project to Poincare
        poincare_embedding = self.project_to_poincare(euclidean_embedding)
        poincare_radius = float(np.linalg.norm(poincare_embedding))

        result = EmbeddingResult(
            euclidean_embedding=euclidean_embedding,
            poincare_embedding=poincare_embedding,
            euclidean_norm=euclidean_norm,
            poincare_radius=poincare_radius,
            embedding_hash=text_hash,
            source=source
        )

        # Cache
        if len(self._cache) >= self._cache_max_size:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[text_hash] = result

        return result

    async def _get_text_embedding(self, text: str) -> np.ndarray:
        """Get CLIP embedding for text."""
        if self._model is None:
            return self._fallback_embedding(text.encode('utf-8'))

        try:
            import torch
            import clip

            text_input = clip.tokenize([text]).to(self._device)

            with torch.no_grad():
                features = self._model.encode_text(text_input)

            return features.cpu().numpy().flatten().astype(np.float32)

        except Exception as e:
            logger.warning(f"CLIP text encoding failed: {e}")
            return self._fallback_embedding(text.encode('utf-8'))

    async def embed_action(
        self,
        action_type: str,
        target: str,
        context_embedding: Optional[np.ndarray] = None
    ) -> EmbeddingResult:
        """
        Embed an action into the Poincare ball.

        Creates an action embedding by combining:
        - Action type encoding
        - Target/selector encoding
        - Optional context from current page state

        Args:
            action_type: Type of action (click, type, navigate, etc.)
            target: Target element or URL
            context_embedding: Optional embedding of current page

        Returns:
            EmbeddingResult for the action
        """
        if not self._is_initialized:
            await self.initialize()

        # Create action description
        action_text = f"{action_type} {target}"

        # Get text embedding
        result = await self.embed_text(action_text, source=f"action:{action_type}")

        # If context is provided, blend with action embedding
        if context_embedding is not None:
            # Simple weighted combination
            blended = 0.7 * result.poincare_embedding + 0.3 * context_embedding
            blended_radius = np.linalg.norm(blended)

            # Re-project if needed
            if blended_radius >= 1.0 - EPSILON:
                blended = blended * (1.0 - EPSILON) / blended_radius
                blended_radius = 1.0 - EPSILON

            result = EmbeddingResult(
                euclidean_embedding=result.euclidean_embedding,
                poincare_embedding=blended,
                euclidean_norm=result.euclidean_norm,
                poincare_radius=blended_radius,
                embedding_hash=result.embedding_hash,
                source=result.source
            )

        return result

    def clear_cache(self):
        """Clear the embedding cache."""
        self._cache.clear()
        logger.info("Embedding cache cleared")


async def create_vision_embedder(
    target_dim: int = 16,
    device: Optional[str] = None
) -> VisionEmbedder:
    """
    Factory function to create and initialize a vision embedder.

    Args:
        target_dim: Target embedding dimension
        device: Compute device

    Returns:
        Initialized VisionEmbedder
    """
    embedder = VisionEmbedder(target_dim=target_dim)
    await embedder.initialize(device=device)
    return embedder
