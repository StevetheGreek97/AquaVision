from core.tools.manual_mask import ManualMask
from core.tools.sam2_masker import SamMasker2
from core.tools.intellignent_scissors import IntelligentScissors

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

        if tool == "manual_mask":
            self.current_tool = ManualMask(self.parent.image_display)
            print('manual has been enabled')
        elif tool == "sam2":
            self.current_tool = SamMasker2(self.parent.image_display)
        elif tool == "intelligent_scissors":
            self.current_tool = IntelligentScissors(self.parent.image_display)
            self.current_tool.set_image(self.parent.state_manager.current_image)

        if self.current_tool:
            self.current_tool.mask_added.connect(self.parent.image_display.refresh_overlay)

    def disable_tools(self):
        """
        Disables all active tools.
        """
        if self.current_tool:
            self.current_tool.clear_temp_items()
            self.current_tool = None
