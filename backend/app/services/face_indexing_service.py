"""Face indexing service (roadmap Phase 8 — Local Face Database).

Ingests images into the local face database: for every detected face it
persists an aligned crop and the embedding to disk, records a DetectedFace
row, and adds the embedding to the FAISS index under the row's primary key.
Afterwards FAISS entity ids map 1:1 to DetectedFace ids.
"""

from pathlib import Path

import cv2
import numpy as np

from app.ai.embedding.face_embedder import FaceEmbedder
from app.ai.vector_db.vector_store import VectorStore
from app.config.settings import Settings
from app.repositories.faces import FaceRepository
from app.repositories.search_history import SearchHistoryRepository


class FaceIndexingService:
    """Grow the local face database from images."""

    def __init__(
        self,
        settings: Settings,
        embedder: FaceEmbedder,
        vector_store: VectorStore,
        face_repo: FaceRepository,
        search_repo: SearchHistoryRepository,
    ) -> None:
        self._settings = settings
        self._embedder = embedder
        self._vector_store = vector_store
        self._face_repo = face_repo
        self._search_repo = search_repo

    async def index_image(self, image_path: str | Path, search_id: int | None = None) -> int:
        """Detect, persist, and index every face in an image.

        Returns the number of faces indexed (0 when no face is detected).
        The transaction commits once at the end.
        """
        path = Path(image_path)
        if not path.is_file():
            raise FileNotFoundError(f"Image not found: {path}")

        if search_id is None:
            search = await self._search_repo.create(uploaded_image=str(path))
            search_id = search.id

        faces = self._embedder.embed_image(path)
        if not faces:
            return 0

        crop_root = self._settings.face_crops_dir / str(search_id)
        embed_root = self._settings.faces_dir / str(search_id)
        crop_root.mkdir(parents=True, exist_ok=True)
        embed_root.mkdir(parents=True, exist_ok=True)

        added: list[tuple[np.ndarray, int]] = []
        for face in faces:
            index = face.face_index + 1
            if face.crop is not None:
                cv2.imwrite(str(crop_root / f"{index}.jpg"), face.crop)
            np.save(embed_root / f"{index}.npy", face.embedding.astype(np.float32))

            db_face = await self._face_repo.create(
                search_id=search_id,
                face_image=f"{search_id}/{index}.jpg",
                embedding_path=f"{search_id}/{index}.npy",
            )
            added.append((face.embedding, db_face.id))

        for embedding, entity_id in added:
            self._vector_store.add(embedding, entity_id)
        self._vector_store.save()

        await self._face_repo.session.commit()
        return len(faces)