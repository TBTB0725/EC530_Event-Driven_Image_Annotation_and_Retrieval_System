from __future__ import annotations

import os
import shutil
import uuid


class ImageStore:
    def __init__(self, base_dir: str = "storage/images") -> None:
        self.base_dir = base_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def save_image(self, source_path: str) -> tuple[str, str]:
        image_id = f"img_{uuid.uuid4().hex[:8]}"
        ext = os.path.splitext(source_path)[1] or ".jpg"
        target_path = os.path.join(self.base_dir, f"{image_id}{ext}")

        shutil.copy(source_path, target_path)
        return image_id, target_path
