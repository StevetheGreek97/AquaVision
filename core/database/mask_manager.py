import numpy as np
import cv2
from time import perf_counter

from services.logger import get_logger

logger = get_logger(__name__)

SQLITE_MAX_VARIABLES = 999  # conservative default; some builds allow 32766
CHUNK_SIZE = 900 

class MaskDatabaseManager:
    """
    Manages mask storage and retrieval.
    """

    def __init__(self, parent, db_connection):
        """
        Initialize with a shared database connection.
        """
        self.db = db_connection  # ✅ Shared DatabaseConnection instance
        self.parent = parent  # Store the parent reference for signal emissions

    def save_mask(self, mask, image_name, class_name="Object"):
        """
        Save a mask to the database.

        Args:
            mask (np.ndarray): The mask to save.
            image_name (str): Name of the image the mask belongs to.
            class_name (str): Class name of the mask.


        """
        surface_area = cv2.contourArea(mask.astype(np.int32))
        mask_bytes = mask.tobytes()  # Convert NumPy array to bytes
        self.db.execute_query(
            "INSERT INTO masks (image_name, mask_data, class_name, surface_area) VALUES (?, ?, ?, ?)",
            (image_name, mask_bytes, class_name, surface_area)
        )
        self.parent.masks_updated.emit()

    def load_masks(self, image_name):
        """
        Load all masks for a given image.

        Returns:
            list of tuples: (id, mask, class_name, surface_area)
        """
        rows = self.db.fetch_all("SELECT id, mask_data, class_name, surface_area FROM masks WHERE image_name = ?", (image_name,))
        
        masks = []
        for row in rows:
            mask_id, mask_data, class_name, surface_area = row
            mask_array = np.frombuffer(mask_data, dtype=np.float32).reshape(-1, 2)
            masks.append((mask_id, mask_array, class_name, surface_area))

        return masks



    def clear_all_masks(self):
        """
        Delete all masks from the database.
        """
        self.db.execute_query("DELETE FROM masks")
        self.parent.masks_updated.emit()

    def rename_mask(self, image_name, mask_id, new_class_name):
        """
        Rename the class of a specific mask.

        Args:
            image_name (str): The name of the image the mask belongs to.
            mask_id (int): The ID of the mask to rename.
            new_class_name (str): The new class name for the mask.
        """
        self.db.execute_query(
            "UPDATE masks SET class_name = ? WHERE image_name = ? AND id = ?",
            (new_class_name, image_name, mask_id)
        )
        self.parent.masks_updated.emit()
    def reindex_masks(self):
        """
        Reindex mask IDs to remove gaps after deletions.
        This resets IDs sequentially (1, 2, 3, ...) and updates SQLite's internal counter.
        """
        self.db.execute_query("PRAGMA foreign_keys = OFF;")  # Disable foreign keys to prevent errors

        self.db.execute_query("""
            WITH Renumbered AS (
                SELECT id, 
                    ROW_NUMBER() OVER (ORDER BY id) AS new_id
                FROM masks
            )
            UPDATE masks
            SET id = (SELECT new_id FROM Renumbered WHERE Renumbered.id = masks.id);
        """)

        self.db.execute_query("DELETE FROM sqlite_sequence WHERE name = 'masks';")  # Reset SQLite's internal counter

        self.db.execute_query("PRAGMA foreign_keys = ON;")  # Re-enable foreign key constraints

        logger.debug("Reindexed mask ids")
        self.parent.masks_updated.emit()

    def delete_masks(self, image_name: str, mask_ids, *, profile: bool = True) -> dict:
        """
        Fast path: delete multiple masks in one transaction.
        Returns profiling info: {'chunks': int, 'rows': int, 'ms': float}
        """
        if isinstance(mask_ids, int):
            mask_ids = [mask_ids]
        if not mask_ids:
            return {'chunks': 0, 'rows': 0, 'ms': 0.0}

        t0 = perf_counter()
        rows_total = 0
        chunks = 0

        # Begin a single transaction for all chunks
        self.db.execute_query("BEGIN IMMEDIATE")

        try:
            # Process in chunks to avoid exceeding SQLite variable limits
            for i in range(0, len(mask_ids), CHUNK_SIZE):
                chunk = mask_ids[i:i+CHUNK_SIZE]
                placeholders = ",".join("?" * len(chunk))
                sql = f"DELETE FROM masks WHERE image_name = ? AND id IN ({placeholders})"
                params = [image_name, *chunk]
                rows = self.db.execute_query(sql, params)  # ensure your db layer supports this
                rows_total += rows if rows is not None else 0
                chunks += 1

            self.db.execute_query("COMMIT")
        except Exception:
            self.db.execute_query("ROLLBACK")
            raise
        finally:
            t1 = perf_counter()

        # Emit once (let your MainApp’s coalesced timer handle heavy refresh)
        self.parent.masks_updated.emit()

        info = {'chunks': chunks, 'rows': rows_total, 'ms': (t1 - t0) * 1000.0}
        if profile:
            logger.debug("delete_masks: %d row(s) in %d chunk(s), %.2f ms",
                         rows_total, chunks, info['ms'])
        return info

    def delete_masks_by_class(self, class_name):
        """
        Delete all masks associated with a specific class name.
        """
        rows = self.db.execute_query("DELETE FROM masks WHERE class_name = ?", (class_name,))
        logger.info("Deleted %d mask(s) of class %r", rows, class_name)
        self.parent.masks_updated.emit()

    def count_masks_by_class(self, class_name):
        """
        Count how many masks are associated with a specific class.
        """
        result = self.db.fetch_one("SELECT COUNT(*) FROM masks WHERE class_name = ?", (class_name,))
        return result[0] if result else 0
