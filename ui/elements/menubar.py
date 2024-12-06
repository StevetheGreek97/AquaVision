from PyQt6.QtWidgets import QMenuBar
from PyQt6.QtGui import QAction


class MenuBar(QMenuBar):
    """
    A custom menu bar with options for File, Actions, View, and Help menus.
    """

    def __init__(self, parent):
        """
        Initialize the MenuBar and set up the menus.

        Args:
            parent: The parent widget (typically the main window).
        """
        super().__init__(parent)
        self.parent = parent

        # Initialize Menus
        self._init_file_menu()
        self._init_actions_menu()
        self._init_view_menu()
        self._init_help_menu()

    def _init_file_menu(self):
        """
        Create the File menu with options for loading, saving, exporting, and exiting.
        """
        file_menu = self.addMenu("File")

        actions = [
            ("Load Images", self.parent.load_images),
            ("Show Results", self.parent.show_results), 
            ("Save Results", None),
            ("Export Results", None),  # Placeholder for future implementation
            ("Exit", self.parent.close),
        ]

        self._add_actions_to_menu(file_menu, actions)

    def _init_actions_menu(self):
        """
        Create the Actions menu with options for running inference and undo/redo.
        """
        actions_menu = self.addMenu("Actions")

    def _init_actions_menu(self):
        actions_menu = self.addMenu("Actions")

        actions = [
            ("Run Inference", lambda: print("Run Inference clicked") or self.parent.popup_inference_dialog(self.parent.models_dir, 'yolo', 'Running inference...')),
            ("Segment Anything", lambda: print("Segment Anything clicked") or self.parent.popup_inference_dialog(self.parent.sam_dir, 'sam', 'Segmenting...'))
        ]

        self._add_actions_to_menu(actions_menu, actions)


    def _init_view_menu(self):
        """
        Create the View menu with options for fullscreen and other view settings.
        """
        view_menu = self.addMenu("View")

        actions = [
            ("Fullscreen Mode", None),  # Placeholder for fullscreen toggle
        ]

        self._add_actions_to_menu(view_menu, actions)

    def _init_help_menu(self):
        """
        Create the Help menu with documentation and about options.
        """
        help_menu = self.addMenu("Help")

        actions = [
            ("Documentation", None),  # Placeholder for documentation
            ("About", None),  # Placeholder for about dialog
        ]

        self._add_actions_to_menu(help_menu, actions)

    def _add_actions_to_menu(self, menu, actions):
        """
        Utility method to add a list of actions to a given menu.

        Args:
            menu: The QMenu to which actions will be added.
            actions: A list of tuples where each tuple contains:
                - action_text (str): The text for the action.
                - callback (callable or None): The function to connect to the action.
        """
        for action_text, callback in actions:
            action = QAction(action_text, self.parent)
            if callback:
                action.triggered.connect(callback)
            menu.addAction(action)
