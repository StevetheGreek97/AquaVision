from core.data import ClassIdx
from PyQt6.QtGui import QColor
class ClassIndexManager:
    def __init__(self):
        self.classes = {}

    def add_class(self, idx, class_name, color):
        """
        Add a new class with a unique index.
        """
        self.classes[idx] = ClassIdx(class_name, color)


    def remove_class(self, idx):
        """
        Remove a class and reindex remaining classes.
        """
        del self.classes[idx]
        self._reindex_classes()

    def _reindex_classes(self):
        """
        Reindex class indices after a removal.
        """
        self.classes = {i: value for i, value in enumerate(self.classes.values())}

    def get_idx_by_name(self, name):
        # Create a reverse lookup dictionary
        reverse_dict = {pair.name: key for key, pair in self.classes.items()}
        # Return the key for the target value1
        return reverse_dict.get(name, 999)
    
    def get_color_by_name(self, name):
        for pair in self.classes.values():
            if pair.name == name:
                return pair.color
            
  
        return QColor(255, 255, 255)


    def get_mask_color(self, class_name):
        """
        Get the color associated with a class.
        """
        pass
    def get_all_class_names(self):
        """
        Get all class names as a list.
        """
        return [pair.name for pair in self.classes.values()]