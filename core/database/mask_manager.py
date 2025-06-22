import numpy as np

class MaskDatabaseManager:
    """
    Manages mask storage and retrieval.
    """

    def __init__(self, db_connection):
        """
        Initialize with a shared database connection.
        """
        self.db = db_connection  # ✅ Shared DatabaseConnection instance
        # Cache masks per image to avoid repeated database queries
        self.cache = {}

    def save_mask(self, mask, image_name, class_name="Object"):
        """
        Save a mask to the database.

        Args:
            mask (np.ndarray): The mask to save.
            image_name (str): Name of the image the mask belongs to.
            class_name (str): Class name of the mask.

        Returns:
            int: ID of the newly saved mask.
        """
        mask_bytes = mask.tobytes()  # Convert NumPy array to bytes
        self.db.execute_query(
            "INSERT INTO masks (image_name, mask_data, class_name) VALUES (?, ?, ?)",
            (image_name, mask_bytes, class_name)
        )
        # Invalidate cache for this image so subsequent loads include the new mask
        self.cache.pop(image_name, None)

    def load_masks(self, image_name):
        """
        Load all masks for a given image.

        Returns:
            list of tuples: (id, mask, class_name)
        """
        if image_name in self.cache:
            return self.cache[image_name]

        rows = self.db.fetch_all(
            "SELECT id, mask_data, class_name FROM masks WHERE image_name = ?",
            (image_name,),
        )

        masks = []
        for row in rows:
            mask_id, mask_data, class_name = row
            mask_array = np.frombuffer(mask_data, dtype=np.float32).reshape(-1, 2)

            if mask_array.shape[0] < 3:
                print(
                    f"❌ Warning: Mask {mask_id} has an invalid shape: {mask_array.shape}"
                )

            masks.append((mask_id, mask_array, class_name))

        self.cache[image_name] = masks
        return masks


    def clear_all_masks(self):
        """
        Delete all masks from the database.
        """
        self.db.execute_query("DELETE FROM masks")
        self.cache.clear()

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
        self.cache.pop(image_name, None)
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

        print("✅ Mask IDs successfully reindexed!")
        self.cache.clear()

    def delete_mask(self, image_name, mask_ids):
        """
        Delete a specific mask or multiple masks from the database.

        Args:
            image_name (str): The name of the image the masks belong to.
            mask_ids (int or list): The ID(s) of the mask(s) to delete.
        """
        if isinstance(mask_ids, int):  # If a single ID is provided, convert to list
            mask_ids = [mask_ids]

        placeholders = ",".join("?" * len(mask_ids))  # Create a dynamic query placeholder (e.g., ?, ?, ?)
        query = f"DELETE FROM masks WHERE image_name = ? AND id IN ({placeholders})"

        self.db.execute_query(query, [image_name] + mask_ids)

        print(f"✅ Deleted mask(s) with ID(s): {mask_ids} from image: {image_name}")
        self.cache.pop(image_name, None)

    def delete_masks_by_class(self, class_name):
        """
        Delete all masks associated with a specific class name.
        """
        self.db.execute_query("DELETE FROM masks WHERE class_name = ?", (class_name,))
        print(f"🗑 Deleted all masks with class name: {class_name}")
        self.cache.clear()

    def count_masks_by_class(self, class_name):
        """
        Count how many masks are associated with a specific class.
        """
        result = self.db.fetch_one("SELECT COUNT(*) FROM masks WHERE class_name = ?", (class_name,))
        return result[0] if result else 0
