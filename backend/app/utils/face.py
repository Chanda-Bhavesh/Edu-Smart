"""
Face recognition utility using DeepFace + OpenCV.

Install dependencies:
    pip install deepface opencv-python-headless numpy

All functions degrade gracefully if the libraries are not installed.
"""
import io
import pickle
from typing import Any


def _imports_available() -> bool:
    try:
        import deepface  # noqa: F401
        import cv2       # noqa: F401
        import numpy     # noqa: F401
        return True
    except ImportError:
        return False


def encode_face_from_bytes(image_bytes: bytes) -> bytes:
    """
    Accept a raw image (JPEG/PNG bytes), extract the face embedding
    using DeepFace (Facenet model), and return the embedding
    serialised as bytes (pickle) for storage in the database.

    Raises ValueError if no face is detected or libraries are missing.
    """
    if not _imports_available():
        raise ValueError("Face recognition libraries (deepface, opencv, numpy) are not installed.")

    import numpy as np
    import cv2
    from deepface import DeepFace

    # Decode bytes → numpy array (BGR image)
    nparr  = np.frombuffer(image_bytes, np.uint8)
    img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_cv is None:
        raise ValueError("Could not decode image. Ensure it is a valid JPEG or PNG.")

    # Extract embedding — raises ValueError internally if no face found
    result    = DeepFace.represent(img_path=img_cv, model_name="Facenet", enforce_detection=True)
    embedding = np.array(result[0]["embedding"])
    return pickle.dumps(embedding)


def recognise_faces_in_image(image_bytes: bytes, encodings: list[dict]) -> list[str]:
    """
    Given a classroom image and a list of known encodings:
        encodings = [{"student_id": "...", "encoding": <bytes>}, ...]

    Returns a list of matched student IDs (those whose face was found in the image).

    Uses cosine distance threshold of 0.4 (Facenet default).
    """
    if not _imports_available():
        raise ValueError("Face recognition libraries are not installed.")

    import numpy as np
    import cv2
    from deepface import DeepFace
    from scipy.spatial.distance import cosine

    nparr  = np.frombuffer(image_bytes, np.uint8)
    img_cv = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img_cv is None:
        raise ValueError("Could not decode image.")

    # Extract all face embeddings found in the classroom image
    try:
        faces = DeepFace.represent(img_path=img_cv, model_name="Facenet", enforce_detection=False)
    except Exception:
        return []

    face_embeddings = [np.array(f["embedding"]) for f in faces]
    if not face_embeddings:
        return []

    THRESHOLD = 0.4
    matched_ids: list[str] = []

    for known in encodings:
        known_vec = pickle.loads(known["encoding"])
        for face_vec in face_embeddings:
            dist = cosine(known_vec, face_vec)
            if dist < THRESHOLD:
                matched_ids.append(known["student_id"])
                break  # stop checking faces for this student once matched

    return matched_ids
