
"""Data layer: the contract every data manager follows.

Importing the class here lets other files write `from data_layer import BaseDataManager`
instead of naming the individual module file each time.
"""

from .base_data_manager import BaseDataManager

__all__ = ["BaseDataManager"]
 