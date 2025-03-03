import os
import numpy as np
import glob

class DataManager:
    """
    Handles the creation, storage, and loading of .dat files for masks.
    """

    def __init__(self, storage_dir='masks'):
        """
        Initialize the MaskStorageHandler.

        Args:
            storage_dir (str): Directory to store .dat mask files.
        """
        self.storage_dir = storage_dir
        os.makedirs(self.storage_dir, exist_ok=True)

    def save_mask(self, mask, image_name, class_name='None'):
        """
        Save a mask to a .dat file with a unique name.

        Args:
            mask (np.ndarray): The mask to save.
            image_name (str): Name of the image the mask belongs to.
            class_name (str): Class name of the mask.

        Returns:
            str: Path to the saved .dat file.
        """
        mask = mask.astype(np.float32)
        
        # Find the next available index
        search_pattern = os.path.join(self.storage_dir, f"{image_name}||mask_*.dat")
        existing_files = glob.glob(search_pattern)
        existing_indices = {
            int(os.path.basename(f).split("||")[1].split("_")[1]) for f in existing_files
        }

        next_index = 1
        while next_index in existing_indices:
            next_index += 1  # Find first unused index

        mask_filename = os.path.join(self.storage_dir, f"{image_name}||mask_{next_index}||{class_name}.dat")

        # Save the mask as a memory-mapped file
        fp = np.memmap(mask_filename, dtype=mask.dtype, mode='w+', shape=mask.shape)
        fp[:] = mask[:]
        fp.flush()

        print(f"Mask saved: {mask_filename}")
        return mask_filename

    def load_mask(self, mask_file):
        """
        Load a mask from a .dat file.

        Args:
            mask_file (str): Path to the .dat file.

        Returns:
            np.ndarray: The loaded mask as a NumPy array.
        """
        if not os.path.exists(mask_file):
            raise FileNotFoundError(f"Mask file not found: {mask_file}")

        # Get mask shape and dtype from the file
        file_size = os.path.getsize(mask_file)
        dtype = np.float32  # Assuming dtype used during saving
        n = file_size // (np.dtype(dtype).itemsize * 2)  # Assuming 2 columns (x, y)
        shape = (n, 2)

        # Load the memory-mapped file
        mask = np.memmap(mask_file, dtype=dtype, mode='r', shape=shape)
        return mask

    def list_masks(self, image_name):
        """
        List all masks associated with a given image.

        Args:
            image_name (str): Name of the image.

        Returns:
            list: Paths to all .dat files for the image's masks.
        """
        search_pattern = os.path.join(self.storage_dir, f"{image_name}||mask_*.dat")
        return glob.glob(search_pattern)

    def delete_mask(self, mask_file):
        """
        Delete a .dat file for a mask.

        Args:
            mask_file (str): Path to the .dat file to delete.
        """
        if os.path.exists(mask_file):
            os.remove(mask_file)
            print(f"Mask deleted: {mask_file}")
        else:
            print(f"Mask file not found: {mask_file}")

    def clear_all_masks(self, image_name=None):
        """
        Clear all masks for a given image or all masks in the directory.

        Args:
            image_name (str, optional): Name of the image. If None, clears all masks.
        """
        if image_name:
            search_pattern = os.path.join(self.storage_dir, f"{image_name}||mask_*.dat")
        else:
            search_pattern = os.path.join(self.storage_dir, "*.dat")

        for mask_file in glob.glob(search_pattern):
            self.delete_mask(mask_file)
            
    def get_masks(self, image_name):
        """
        Retrieve all masks associated with a given image.

        Args:
            image_name (str): Name of the image (without extension).

        Returns:
            list: A list of NumPy arrays, each representing a mask.
        """
        mask_files = self.list_masks(image_name)
        masks = [self.load_mask(mask_file) for mask_file in mask_files]
        return masks


    def reindex_masks(self, image_name):
        """
        Reindex the mask IDs for the given image after masks are deleted.
        Ensures contiguous numbering while preventing overwrites.
        
        Args:
            image_name (str): Name of the image whose masks need reindexing.
        """
        mask_files = self.list_masks(image_name)

        # Extract and sort existing mask indices
        indexed_masks = []
        for mask_file in mask_files:
            filename = os.path.basename(mask_file)
            parts = filename.split("||")
            if len(parts) < 3:
                continue  # Skip invalid files
            
            try:
                mask_index = int(parts[1].split("_")[1])  # Extract mask index
            except ValueError:
                continue  # Skip if not a valid integer

            indexed_masks.append((mask_index, mask_file, parts[2].replace('.dat', '')))  # Store (index, path, class)

        if not indexed_masks:
            return  # No masks to reindex

        # Sort by existing mask index
        indexed_masks.sort()

        # Find the lowest missing index
        used_indices = {idx for idx, _, _ in indexed_masks}
        available_index = 1  # Start reindexing from 1

        for old_index, mask_file, class_name in indexed_masks:
            if available_index in used_indices:
                available_index += 1  # Move to the next available slot
            
            if old_index != available_index:
                new_filename = os.path.join(self.storage_dir, f"{image_name}||mask_{available_index}||{class_name}.dat")
                os.rename(mask_file, new_filename)
                print(f"Renamed mask_{old_index} to mask_{available_index}")

            used_indices.add(available_index)


    def rename_class(self, image_name, mask_id, new_class_name):
        """
        Rename the class name for a given mask file.

        Args:
            image_name (str): Name of the image associated with the mask.
            mask_id (str): Mask ID (e.g., "mask_1").
            new_class_name (str): New class name.
        """
        # Search for the mask file
        search_pattern = os.path.join(self.storage_dir, f"{image_name}||{mask_id}||*.dat")
        mask_files = glob.glob(search_pattern)

        if not mask_files:
            print(f"No mask file found for {mask_id}")
            return

        # Rename the mask file
        old_file = mask_files[0]
        parts = os.path.basename(old_file).split("||")
        new_filename = os.path.join(self.storage_dir, f"{parts[0]}||{parts[1]}||{new_class_name}.dat")
        os.rename(old_file, new_filename)
        
class ClassIdx:
    __slots__ = ('name', 'color')
    def __init__(self, name, color):
        self.name = name
        self.color = color