from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from core.tools.manual_mask import ManualMask
from core.tools.sam2_masker import SamMasker2
from core.tools.intellignent_scissors import IntelligentScissors
from core.tools.sam2_boxmasker import SamBoxMasker
from core.tools.dextr_mask import DEXTRMasker
from services.logger import get_logger

logger = get_logger(__name__)

class ToolManager:
    """
    Handles activation and deactivation of image processing tools.
    """

    def __init__(self, parent):
        self.parent = parent
        self.current_tool = None

    def enable_tool(self, tool):
        """
        Enables a tool and disables others.
        """
        self.disable_tools()

        # Show wait cursor
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)


        try:
            if tool == "manual_mask":
                self.current_tool = ManualMask(self.parent.image_display)
            elif tool == "sam2":
                self.current_tool = SamMasker2(self.parent.image_display)
            elif tool == "sam2_box":
                self.current_tool = SamBoxMasker(self.parent.image_display)
            elif tool == "dextr":
                self.current_tool = DEXTRMasker(self.parent.image_display)
            elif tool == "intelligent_scissors":
                self.current_tool = IntelligentScissors(self.parent.image_display)
                self.current_tool.set_image(self.parent.state_manager.current_image)
            else:
                logger.warning("Unknown tool requested: %r", tool)

            if self.current_tool:
                self.current_tool.mask_added.connect(self.parent.image_display.refresh_overlay)
                logger.info("Enabled tool: %s", tool)
        except Exception:
            logger.exception("Failed to enable tool %r (model load error?)", tool)
            self.current_tool = None
        finally:
            QApplication.restoreOverrideCursor()



    def disable_tools(self):
        """
        Disables all active tools.
        """
        if self.current_tool:
            self.current_tool.clear_temp_items()
            self.current_tool = None
