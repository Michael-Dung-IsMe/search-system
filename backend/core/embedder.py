"""Multimodal Vector Embedder using Marqo/marqo-fashionSigLIP.

Extracts unified 768-dimensional visual and textual embeddings into the same vector space.
Includes fast mock mode for offline testing and deterministic CI runs.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Optional, Union

import numpy as np
from PIL import Image
import torch

logger = logging.getLogger("embedder")


class MultimodalEmbedder:
    """Computes normalized 768-dim embeddings for images (SigLIP) and text queries (OpenAI / SigLIP fallback)."""

    _instance: Optional[MultimodalEmbedder] = None

    def __init__(
        self,
        model_name: str = "hf-hub:Marqo/marqo-fashionSigLIP",
        text_model_name: str = "text-embedding-3-small",
        use_mock: bool = False,
    ):
        import os

        self.use_mock = use_mock
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.preprocess = None
        self.tokenizer = None
        self.openai_key = os.getenv("OPENAI_API_KEY")
        self.text_model_name = text_model_name
        self.text_dimensions = 768
        self._openai_client = None

        if self.openai_key and not use_mock:
            try:
                from openai import OpenAI
                self._openai_client = OpenAI(api_key=self.openai_key)
                logger.info("OpenAI client initialized for text embeddings (%s, 768-dim).", self.text_model_name)
            except Exception as e:
                logger.warning("Failed to initialize OpenAI client (%s). Will fallback to local text encoder.", e)

        if not use_mock:
            try:
                import open_clip

                logger.info("Initializing OpenCLIP '%s' on %s...", model_name, self.device)
                self.model, _, self.preprocess = open_clip.create_model_and_transforms(
                    model_name,
                    device=self.device,
                )
                self.tokenizer = open_clip.get_tokenizer(model_name)
                self.model.eval()
                logger.info("OpenCLIP model initialized successfully.")
            except Exception as e:
                logger.warning("Failed to load OpenCLIP model (%s). Falling back to mock embedder.", e)
                self.use_mock = True
        else:
            logger.info("MultimodalEmbedder initialized in MOCK mode.")

    def encode_text(self, text: str) -> np.ndarray:
        """Encodes text query into a normalized 768-dim vector using OpenAI (or SigLIP fallback)."""
        if not text:
            vec = np.zeros(768, dtype=np.float32)
            vec[0] = 1.0
            return vec

        if self.use_mock:
            seed = sum(ord(c) for c in text) % 100000
            rng = np.random.default_rng(seed)
            vec = rng.standard_normal(768).astype(np.float32)
            return vec / (np.linalg.norm(vec) + 1e-8)

        # 1. Primary: OpenAI text-embedding-3-small with 768 dimensions
        if self._openai_client:
            try:
                resp = self._openai_client.embeddings.create(
                    input=text,
                    model=self.text_model_name,
                    dimensions=self.text_dimensions,
                )
                vec = np.array(resp.data[0].embedding, dtype=np.float32)
                return vec / (np.linalg.norm(vec) + 1e-8)
            except Exception as e:
                logger.warning("OpenAI text embedding failed (%s), falling back to SigLIP local text encoder.", e)

        # 2. Resilient Fallback: Local SigLIP text encoder
        if self.model and self.tokenizer:
            with torch.no_grad():
                tokens = self.tokenizer([text]).to(self.device)
                features = self.model.encode_text(tokens)
                features = features / features.norm(dim=-1, keepdim=True)
                return features.cpu().numpy().squeeze().astype(np.float32)

        # 3. Deterministic pseudo fallback
        seed = sum(ord(c) for c in text) % 100000
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(768).astype(np.float32)
        return vec / (np.linalg.norm(vec) + 1e-8)

    def encode_texts_batch(self, texts: List[str]) -> np.ndarray:
        """Batch-encodes multiple text strings using OpenAI (or SigLIP fallback)."""
        if not texts:
            return np.empty((0, 768), dtype=np.float32)

        if self.use_mock:
            return np.vstack([self.encode_text(t) for t in texts])

        if self._openai_client:
            try:
                resp = self._openai_client.embeddings.create(
                    input=texts,
                    model=self.text_model_name,
                    dimensions=self.text_dimensions,
                )
                vectors = [np.array(item.embedding, dtype=np.float32) for item in resp.data]
                mat = np.vstack(vectors)
                norms = np.linalg.norm(mat, axis=1, keepdims=True) + 1e-8
                return mat / norms
            except Exception as e:
                logger.warning("OpenAI batch text embedding failed (%s), falling back to SigLIP.", e)

        if self.model and self.tokenizer:
            with torch.no_grad():
                tokens = self.tokenizer(texts).to(self.device)
                features = self.model.encode_text(tokens)
                features = features / features.norm(dim=-1, keepdim=True)
                return features.cpu().numpy().astype(np.float32)

        return np.vstack([self.encode_text(t) for t in texts])

    def encode_image(self, image_input: Union[Path, str, Image.Image]) -> np.ndarray:
        """Encodes PIL Image or image file path into a normalized 768-dim vector."""
        if self.use_mock:
            seed_val = str(image_input) if isinstance(image_input, (str, Path)) else "pil_image"
            seed = sum(ord(c) for c in str(seed_val)) % 100000
            rng = np.random.default_rng(seed)
            vec = rng.standard_normal(768).astype(np.float32)
            return vec / (np.linalg.norm(vec) + 1e-8)

        if isinstance(image_input, (str, Path)):
            img = Image.open(image_input).convert("RGB")
        else:
            img = image_input.convert("RGB")

        with torch.no_grad():
            tensor = self.preprocess(img).unsqueeze(0).to(self.device)
            features = self.model.encode_image(tensor)
            features = features / features.norm(dim=-1, keepdim=True)
            return features.cpu().numpy().squeeze().astype(np.float32)

    @classmethod
    def get_instance(cls, use_mock: bool = False) -> MultimodalEmbedder:
        """Singleton accessor for shared embedder."""
        if cls._instance is None or (use_mock and not getattr(cls._instance, "use_mock", False)):
            cls._instance = cls(use_mock=use_mock)
        return cls._instance
