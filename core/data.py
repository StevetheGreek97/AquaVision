from dataclasses import dataclass, field
from typing import List, Tuple
import numpy as np

#@dataclass
#class ImageMask:
 #   """
 #   Represents the masks and colors for a single image.
 #   """
  #  masks: List[np.ndarray] = field(default_factory=list)  # List of masks as numpy arrays
  #  colors: List[Tuple[int, int, int]] = field(default_factory=list)  # List of RGB colors

from dataclasses import dataclass, field
import numpy as np
from typing import List, Tuple
import os

@dataclass
class ImageMask:
    """
    Represents the masks and colors for a single image using numpy.memmap for memory efficiency.
    """

    masks: List[np.memmap] = field(default_factory=list)  # List of masks stored as memmaps
   