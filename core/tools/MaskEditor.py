import numpy as np
from core.data import DataManager
import os
class MaskEditor:
    def __init__(self, mask, mask_id, image_name, class_name):
        self.mask = mask
        self.mask_id = mask_id
        self.image_name = image_name
        self.class_name = class_name
        self.mask_file = f'masks/{image_name}||{mask_id}||{class_name}.dat'



        self.current_edit_mask = None



        self.is_editing = False
        self.dragged_vertex_index = None

    def start_editing(self):
        """
        Start editing a specific mask.
        """
        self.current_edit_mask = self.mask.copy()  # Work with a copy to avoid unintended changes
        self.is_editing = True
        print(f"Started editing mask: {self.mask_file}")



    def stop_editing(self):
        """
        Stop editing mode and save the final mask.
        """

        self.is_editing = False
        self.current_edit_mask = None
        self.mask = None
        self.mask_id = None
        self.image_name = None
        self.class_name = None
        self.mask_file = None

        self.dragged_vertex_index = None
        print("Stopped editing mode.")

    def save_current_mask(self):
        """
        Save the current mask live to its corresponding file, overriding the existing file.
        """
        if self.current_edit_mask is None or self.mask_file is None:
            print("No mask to save.")
            return

        # Use DataManager's save_mask method to save the updated mask
        data_manager = DataManager()
        data_manager.save_mask(self.current_edit_mask, self.image_name, class_name=self.class_name, mask_index = int(self.mask_id.split("_")[1]))
        
    def find_nearest_vertex(self, point):
        """
        Find the nearest vertex in the mask to the given point.
        """
        if self.current_edit_mask is None:
            return None
        distances = [np.linalg.norm(np.array(p) - np.array(point)) for p in self.current_edit_mask]
        return np.argmin(distances)

    def update_vertex(self, vertex_index, new_position):
        """
        Update the position of a specific vertex and save the changes.
        """
        if self.current_edit_mask is not None and vertex_index is not None:
            self.current_edit_mask[vertex_index] = new_position
            print(f"Updated vertex {vertex_index} to {new_position}")

    def add_vertex(self, point):
        """
        Add a new vertex to the mask at the specified position.
        The vertex is inserted between the two nearest existing vertices.
        """
        if self.current_edit_mask is None:
            print("No mask available to add a vertex.")
            return

        # Find the closest edge to insert the new vertex
        min_distance = float('inf')
        insert_index = 0

        for i in range(len(self.current_edit_mask)):
            start_point = np.array(self.current_edit_mask[i])
            end_point = np.array(self.current_edit_mask[(i + 1) % len(self.current_edit_mask)])
            distance = self._point_to_segment_distance(point, start_point, end_point)

            if distance < min_distance:
                min_distance = distance
                insert_index = i + 1

        # Insert the new point
        self.current_edit_mask = np.insert(self.current_edit_mask, insert_index, [point], axis=0)
        print(f"Added vertex at {point} between vertices {insert_index - 1} and {insert_index}")


    def delete_vertex(self, vertex_index):
        if self.current_edit_mask is not None and vertex_index is not None:
            self.current_edit_mask = np.delete(self.current_edit_mask, vertex_index, axis=0)
            print(f"Deleted vertex at index {vertex_index}")
    def get_current_mask(self):
        """
        Return the current mask being edited.
        """
        return self.current_edit_mask
    
    def _point_to_segment_distance(self, point, start, end):
        """
        Calculate the distance from a point to a line segment.
        """
        segment = end - start
        length_squared = np.dot(segment, segment)
        if length_squared == 0:
            return np.linalg.norm(point - start)  # Start and end are the same point

        t = max(0, min(1, np.dot(point - start, segment) / length_squared))
        projection = start + t * segment
        return np.linalg.norm(point - projection)
