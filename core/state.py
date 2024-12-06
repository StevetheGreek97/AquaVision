from core.data import ImageMask
import numpy as np
from tempfile import mkdtemp
import os
import glob
class StateManager:
    """
    Manages the application state including the current image index, path, and associated masks and colors.
    """

    def __init__(self):
        # Initialize state variables
        self.image_index = -1  # Index of the currently displayed image (-1 means no image loaded)
        self.image_masks = {}  # Dictionary of masks by image path
        self.image_paths = []
        self.scissors_points = {}  # Store scissors points for each image
        self._current_image = None  # NumPy array of the current image
    
    @property
    def current_image(self):
        """
        Get the NumPy array of the current image.

        Returns:
            np.ndarray: The image data, or None if no image is loaded.
        """
        return self._current_image


    @current_image.setter
    def current_image(self, image):
        """
        Set the current image.

        Args:
            image (np.ndarray): The image data.
        """
        self._current_image = image

    def set_image_paths(self, image_paths):
        """
        Set the list of image paths and reset the index.

        Args:
            image_paths (list): List of image file paths.
        """
        self.image_paths = image_paths
        self.image_index = 0 if image_paths else -1  # Reset to the first image if the list is not empty

    @property
    def current_image_path(self):
        """
        Get the path of the currently displayed image.

        Returns:
            str: Path of the current image, or None if no image is loaded.
        """
        if 0 <= self.image_index < len(self.image_paths):
            return self.image_paths[self.image_index]
        return None

    @property
    def current_image_index(self):
        """
        Get the index of the currently displayed image.

        Returns:
            int: Index of the current image, or -1 if no image is loaded.
        """
        return self.image_index

    @property
    def current_masks(self):
        """
        Get the masks associated with the currently displayed image.

        Returns:
            list: List of masks for the current image, or an empty list if no masks are available.
        """
        return self.image_masks.get(self.current_image_path, [])

    @property
    def current_colors(self):
        """
        Get the colors associated with the masks of the currently displayed image.

        Returns:
            list: List of colors for the current image's masks, or an empty list if no colors are available.
        """
        return self.colors.get(self.current_image_path, [])

    def next_image(self):
        """
        Navigate to the next image in the list.

        Returns:
            str: Path of the new current image, or None if at the end of the list.
        """
        if self.image_index < len(self.image_paths) - 1:
            self.image_index += 1
            return self.current_image_path
        return None

    def previous_image(self):
        """
        Navigate to the previous image in the list.

        Returns:
            str: Path of the new current image, or None if at the beginning of the list.
        """
        if self.image_index > 0:
            self.image_index -= 1
            return self.current_image_path
        return None
    def add_mask(self, mask, image_path= None):
        """
        Add a mask for the current image and ensure it is properly saved
        without overwriting existing masks.

        Args:
            mask (np.ndarray): The mask to add, as a NumPy array.
        """
        # Ensure a current image path exists
        
        if not image_path: #if  None -> True
            image_path = self.current_image_path
        if not mask.any():
            return
   
            
        # Ensure the masks directory exists
        masks_dir = os.path.join(os.getcwd(), 'masks')
        os.makedirs(masks_dir, exist_ok=True)

        # Use the current image's file name as a base for mask files
        image_name = os.path.splitext(os.path.basename(image_path))[0]
        #search_pattern = os.path.join(masks_dir, f"{image_name}*")
        # Generate a unique filename for the mask
        existing_masks = self.image_masks.get(image_path)
        #matching_files = glob.glob(search_pattern)
        mask_index = len(existing_masks.masks) if existing_masks else 0
        mask_filename = os.path.join(masks_dir, f"{image_name}_mask_{mask_index + 1}.dat")

        # Save the mask as a memory-mapped file
        fp = np.memmap(mask_filename, dtype=mask.dtype, mode='w+', shape=mask.shape)
        fp[:] = mask[:]
        fp.flush()

        # If no masks exist for this image, create a new ImageMask instance
        if image_path not in self.image_masks:
            self.image_masks[image_path] = ImageMask()

        # Append the new memory-mapped mask to the ImageMask instance
        self.image_masks[image_path].masks.append(fp)

        print(f"Mask added: {mask_filename}")

    def add_masks(self, masks, image_path):
        """
        Add multiple masks and their associated colors to the specified image.

        Args:
            image_path (str): Path of the image to associate the masks with.
            masks (list of list of tuple): A list of masks, where each mask is a list of (x, y) coordinates.
            colors (list of tuple): List of colors for the masks, each as an (R, G, B) tuple.
        """
        for mask in masks:
            self.add_mask(mask, image_path)





    def clear_masks(self, image_path):
        """
        Clear all masks and colors for a specified image.

        Args:
            image_path (str): Path of the image to clear masks for.
        """
        if image_path in self.masks:
            self.masks[image_path] = []


    def reset(self):
        """
        Reset all state to the initial empty values.
        """
        self.image_index = -1
        self.image_paths = []
        self.masks.clear()
        self.colors.clear()


