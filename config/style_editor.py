"""
Style Editor Dialog - Visual interface for creating and editing custom styles
"""

import os
import importlib
import sys
from pathlib import Path
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QLabel, QListWidget, QColorDialog, QLineEdit, 
                             QMessageBox, QTabWidget, QWidget, QGridLayout,
                             QScrollArea, QGroupBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


class StyleEditorWidget(QWidget):
    """Embedded style editor widget for use in tabs"""
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.current_style_name = None
        self.current_colors = {}
        self.color_buttons = {}
        
        self.setup_ui()
        self.load_styles_list()
    
    def setup_ui(self):
        """Setup the UI with style selection and color editor"""
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Top section: Style management
        top_section = QHBoxLayout()
        
        # Left: Style list
        list_group = QGroupBox("Available Styles")
        list_layout = QVBoxLayout()
        
        self.style_list = QListWidget()
        self.style_list.currentItemChanged.connect(self.on_style_selected)
        list_layout.addWidget(self.style_list)
        
        list_group.setLayout(list_layout)
        
        # Right: Actions
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout()
        
        self.duplicate_btn = QPushButton("Duplicate Selected")
        self.duplicate_btn.clicked.connect(self.duplicate_style)
        
        self.delete_btn = QPushButton("Delete Custom")
        self.delete_btn.clicked.connect(self.delete_style)
        self.delete_btn.setEnabled(False)
        
        self.new_name_input = QLineEdit()
        self.new_name_input.setPlaceholderText("New style name...")
        
        actions_layout.addWidget(QLabel("Select a style to duplicate:"))
        actions_layout.addWidget(self.new_name_input)
        actions_layout.addWidget(self.duplicate_btn)
        actions_layout.addWidget(QLabel(""))
        actions_layout.addWidget(self.delete_btn)
        actions_layout.addStretch()
        
        actions_group.setLayout(actions_layout)
        
        top_section.addWidget(list_group, 2)
        top_section.addWidget(actions_group, 1)
        
        # Bottom section: Color editor
        editor_group = QGroupBox("Color Editor")
        editor_layout = QVBoxLayout()
        
        # Scroll area for colors
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.colors_grid = QGridLayout()
        scroll_widget.setLayout(self.colors_grid)
        scroll.setWidget(scroll_widget)
        
        editor_layout.addWidget(scroll)
        editor_group.setLayout(editor_layout)
        
        main_layout.addLayout(top_section, 1)
        main_layout.addWidget(editor_group, 2)
        
        self.setLayout(main_layout)
    
    def load_styles_list(self):
        """Load all available styles (built-in + custom)"""
        # Disconnect signal temporarily to avoid triggering style change
        self.style_list.currentItemChanged.disconnect(self.on_style_selected)
        
        self.style_list.clear()
        
        # Built-in styles (read-only)
        self.style_list.addItem("🔒 dark (built-in)")
        self.style_list.addItem("🔒 light (built-in)")
        
        # Custom styles
        custom_dir = Path(__file__).parent / 'custom_styles'
        if custom_dir.exists():
            for file in custom_dir.glob('*.py'):
                if file.name != '__init__.py':
                    style_name = file.stem
                    self.style_list.addItem(f"✏️ {style_name}")
        
        # Select the current active style
        current_style = self.config.get('current_style')
        if current_style:
            # Find and select the item matching current style
            for i in range(self.style_list.count()):
                item_text = self.style_list.item(i).text()
                # Extract style name from "🔒 dark (built-in)" or "✏️ custom_name"
                if current_style in item_text:
                    self.style_list.setCurrentRow(i)
                    # Load colors for display without changing the style
                    self.current_style_name = current_style
                    self.load_style_colors(current_style)
                    # Enable/disable delete button
                    if item_text.startswith("🔒"):
                        self.delete_btn.setEnabled(False)
                    else:
                        self.delete_btn.setEnabled(True)
                    break
        
        # Reconnect signal
        self.style_list.currentItemChanged.connect(self.on_style_selected)
    
    def on_style_selected(self, current, previous):
        """When a style is selected, load its colors"""
        if not current:
            return
        
        style_text = current.text()
        
        # Extract style name
        if style_text.startswith("🔒"):
            self.current_style_name = style_text.split()[1]
            self.delete_btn.setEnabled(False)
        elif style_text.startswith("✏️"):
            self.current_style_name = style_text.split()[1]
            self.delete_btn.setEnabled(True)
        else:
            return
        
        # Load colors from the style
        self.load_style_colors(self.current_style_name)
        
        # Set as current style immediately
        self.config.set_current_style(self.current_style_name)
        
        # Notify parent to refresh UI
        self.notify_style_change()
    
    def notify_style_change(self):
        """Notify parent window to refresh with new style"""
        # Find MainWindow and refresh
        parent = self.parent()
        while parent:
            if parent.__class__.__name__ == 'MainWindow':
                parent.apply_styles()
                break
            parent = parent.parent() if hasattr(parent, 'parent') else None
    
    def load_style_colors(self, style_name):
        """Load colors from a style module"""
        try:
            if style_name == 'dark':
                from config import styles_dark as style_module
            elif style_name == 'light':
                from config import styles_light as style_module
            else:
                # Custom style
                custom_module = __import__(f'config.custom_styles.{style_name}', fromlist=[style_name])
                style_module = custom_module
            
            # Get COLORS dict
            self.current_colors = style_module.COLORS.copy()
            self.display_color_editor()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load style: {e}")
    
    def display_color_editor(self):
        """Display color editor with all colors"""
        # Clear existing widgets
        while self.colors_grid.count():
            item = self.colors_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.color_buttons.clear()
        
        # Create color pickers for each color
        row = 0
        for color_name, color_value in self.current_colors.items():
            # Label
            label = QLabel(color_name + ":")
            label.setMinimumWidth(150)
            
            # Color button
            color_btn = QPushButton()
            color_btn.setFixedSize(80, 30)
            color_btn.setStyleSheet(f"background-color: {color_value}; border: 1px solid #888;")
            color_btn.clicked.connect(lambda checked, name=color_name: self.pick_color(name))
            
            # Value label
            value_label = QLabel(color_value)
            value_label.setMinimumWidth(80)
            
            self.colors_grid.addWidget(label, row, 0)
            self.colors_grid.addWidget(color_btn, row, 1)
            self.colors_grid.addWidget(value_label, row, 2)
            
            self.color_buttons[color_name] = (color_btn, value_label)
            row += 1
    
    def pick_color(self, color_name):
        """Open color picker for a specific color"""
        # Can't modify built-in styles
        if self.current_style_name in ['dark', 'light']:
            QMessageBox.information(
                self, 
                "Read-Only Style", 
                "Built-in styles (dark/light) cannot be modified.\n\nPlease duplicate this style first to create a custom version you can edit."
            )
            return
        
        current_color = self.current_colors[color_name]
        qcolor = QColor(current_color)
        
        color = QColorDialog.getColor(qcolor, self, f"Pick color for {color_name}")
        
        if color.isValid():
            color_hex = color.name()
            self.current_colors[color_name] = color_hex
            
            # Update button and label
            btn, label = self.color_buttons[color_name]
            btn.setStyleSheet(f"background-color: {color_hex}; border: 1px solid #888;")
            label.setText(color_hex)
            
            # IMPORTANT: Save changes immediately to file
            self.save_style_to_file(self.current_style_name, self.current_colors)
            
            # Refresh UI to apply the new color
            self.notify_style_change()
    
    def duplicate_style(self):
        """Duplicate the selected style with a new name"""
        if not self.current_style_name:
            QMessageBox.warning(self, "Warning", "Please select a style to duplicate")
            return
        
        new_name = self.new_name_input.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Warning", "Please enter a name for the new style")
            return
        
        # BUG FIX 1: Prevent using reserved names
        if new_name.lower() in ['dark', 'light']:
            QMessageBox.warning(
                self, 
                "Reserved Name", 
                f"'{new_name}' is a reserved built-in style name.\n\nPlease choose a different name for your custom style."
            )
            return
        
        # Validate name (alphanumeric + underscore)
        if not new_name.replace('_', '').isalnum():
            QMessageBox.warning(self, "Warning", "Style name must be alphanumeric (underscores allowed)")
            return
        
        # Check if already exists
        custom_dir = Path(__file__).parent / 'custom_styles'
        new_file = custom_dir / f'{new_name}.py'
        if new_file.exists():
            QMessageBox.warning(self, "Warning", f"Style '{new_name}' already exists")
            return
        
        # Create new style file
        self.save_style_to_file(new_name, self.current_colors)
        
        # Reload list and select new style
        self.load_styles_list()
        self.new_name_input.clear()
        
    
    def delete_style(self):
        """Delete the selected custom style"""
        if not self.current_style_name:
            return
        
        # Can't delete built-in styles
        if self.current_style_name in ['dark', 'light']:
            QMessageBox.warning(self, "Warning", "Cannot delete built-in styles")
            return
        
        reply = QMessageBox.question(
            self, 
            "Confirm Delete", 
            f"Delete style '{self.current_style_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            custom_dir = Path(__file__).parent / 'custom_styles'
            file_to_delete = custom_dir / f'{self.current_style_name}.py'
            
            try:
                file_to_delete.unlink()
                self.load_styles_list()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {e}")
    
    def save_style_to_file(self, style_name, colors):
        """Save a style to a Python file"""
        custom_dir = Path(__file__).parent / 'custom_styles'
        custom_dir.mkdir(exist_ok=True)
        
        file_path = custom_dir / f'{style_name}.py'
        
        # Generate Python file content
        content = f'''# Custom style: {style_name}
# Auto-generated by Style Editor

COLORS = {{
'''
        for color_name, color_value in colors.items():
            content += f"    '{color_name}': '{color_value}',\n"
        
        content += "}\n\n"
        content += "from pathlib import Path as _Path\n"
        content += "exec((_Path(__file__).parent.parent / 'styles_base_layout.py').read_text(encoding='utf-8'))\n"
        
        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # CRITICAL: Reload the module so changes are immediately visible
        module_name = f'config.custom_styles.{style_name}'
        if module_name in sys.modules:
            importlib.reload(sys.modules[module_name])
        else:
            # Import it for the first time
            __import__(module_name)


class StyleEditorDialog(QDialog):
    """Dialog for creating and editing custom styles"""
    
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.current_style_name = None
        self.current_colors = {}
        self.color_buttons = {}
        
        self.setWindowTitle("Style Editor")
        self.setModal(True)
        self.setMinimumSize(700, 600)
        
        self.setup_ui()
        self.load_styles_list()
    
    def setup_ui(self):
        """Setup the UI with style selection and color editor"""
        main_layout = QVBoxLayout()
        
        # Top section: Style management
        top_section = QHBoxLayout()
        
        # Left: Style list
        list_group = QGroupBox("Available Styles")
        list_layout = QVBoxLayout()
        
        self.style_list = QListWidget()
        self.style_list.currentItemChanged.connect(self.on_style_selected)
        list_layout.addWidget(self.style_list)
        
        list_group.setLayout(list_layout)
        
        # Right: Actions
        actions_group = QGroupBox("Actions")
        actions_layout = QVBoxLayout()
        
        self.duplicate_btn = QPushButton("Duplicate Selected")
        self.duplicate_btn.clicked.connect(self.duplicate_style)
        
        self.delete_btn = QPushButton("Delete Custom")
        self.delete_btn.clicked.connect(self.delete_style)
        self.delete_btn.setEnabled(False)
        
        self.new_name_input = QLineEdit()
        self.new_name_input.setPlaceholderText("New style name...")
        
        actions_layout.addWidget(QLabel("Select a style to duplicate:"))
        actions_layout.addWidget(self.new_name_input)
        actions_layout.addWidget(self.duplicate_btn)
        actions_layout.addWidget(QLabel(""))
        actions_layout.addWidget(self.delete_btn)
        actions_layout.addStretch()
        
        actions_group.setLayout(actions_layout)
        
        top_section.addWidget(list_group, 2)
        top_section.addWidget(actions_group, 1)
        
        # Bottom section: Color editor
        editor_group = QGroupBox("Color Editor")
        editor_layout = QVBoxLayout()
        
        # Scroll area for colors
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        self.colors_grid = QGridLayout()
        scroll_widget.setLayout(self.colors_grid)
        scroll.setWidget(scroll_widget)
        
        editor_layout.addWidget(scroll)
        editor_group.setLayout(editor_layout)
        
        # Close button
        close_btn = QPushButton("Apply and Close")
        close_btn.clicked.connect(self.apply_and_close)
        
        main_layout.addLayout(top_section, 1)
        main_layout.addWidget(editor_group, 2)
        main_layout.addWidget(close_btn)
        
        self.setLayout(main_layout)
    
    def load_styles_list(self):
        """Load all available styles (built-in + custom)"""
        # Disconnect signal temporarily to avoid triggering style change
        self.style_list.currentItemChanged.disconnect(self.on_style_selected)
        
        self.style_list.clear()
        
        # Built-in styles (read-only)
        self.style_list.addItem("🔒 dark (built-in)")
        self.style_list.addItem("🔒 light (built-in)")
        
        # Custom styles
        custom_dir = Path(__file__).parent / 'custom_styles'
        if custom_dir.exists():
            for file in custom_dir.glob('*.py'):
                if file.name != '__init__.py':
                    style_name = file.stem
                    self.style_list.addItem(f"✏️ {style_name}")
        
        # Select the current active style
        current_style = self.config.get('current_style')
        if current_style:
            # Find and select the item matching current style
            for i in range(self.style_list.count()):
                item_text = self.style_list.item(i).text()
                # Extract style name from "🔒 dark (built-in)" or "✏️ custom_name"
                if current_style in item_text:
                    self.style_list.setCurrentRow(i)
                    # Load colors for display without changing the style
                    self.current_style_name = current_style
                    self.load_style_colors(current_style)
                    # Enable/disable delete button
                    if item_text.startswith("🔒"):
                        self.delete_btn.setEnabled(False)
                    else:
                        self.delete_btn.setEnabled(True)
                    break
        
        # Reconnect signal
        self.style_list.currentItemChanged.connect(self.on_style_selected)
    
    def on_style_selected(self, current, previous):
        """When a style is selected, load its colors"""
        if not current:
            return
        
        style_text = current.text()
        
        # Extract style name
        if style_text.startswith("🔒"):
            self.current_style_name = style_text.split()[1]
            self.delete_btn.setEnabled(False)
        elif style_text.startswith("✏️"):
            self.current_style_name = style_text.split()[1]
            self.delete_btn.setEnabled(True)
        else:
            return
        
        # Load colors from the style
        self.load_style_colors(self.current_style_name)
    
    def load_style_colors(self, style_name):
        """Load colors from a style module"""
        try:
            if style_name == 'dark':
                from config import styles_dark as style_module
            elif style_name == 'light':
                from config import styles_light as style_module
            else:
                # Custom style
                custom_module = __import__(f'config.custom_styles.{style_name}', fromlist=[style_name])
                style_module = custom_module
            
            # Get COLORS dict
            self.current_colors = style_module.COLORS.copy()
            self.display_color_editor()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to load style: {e}")
    
    def display_color_editor(self):
        """Display color editor with all colors"""
        # Clear existing widgets
        while self.colors_grid.count():
            item = self.colors_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.color_buttons.clear()
        
        # Create color pickers for each color
        row = 0
        for color_name, color_value in self.current_colors.items():
            # Label
            label = QLabel(color_name + ":")
            label.setMinimumWidth(150)
            
            # Color button
            color_btn = QPushButton()
            color_btn.setFixedSize(80, 30)
            color_btn.setStyleSheet(f"background-color: {color_value}; border: 1px solid #888;")
            color_btn.clicked.connect(lambda checked, name=color_name: self.pick_color(name))
            
            # Value label
            value_label = QLabel(color_value)
            value_label.setMinimumWidth(80)
            
            self.colors_grid.addWidget(label, row, 0)
            self.colors_grid.addWidget(color_btn, row, 1)
            self.colors_grid.addWidget(value_label, row, 2)
            
            self.color_buttons[color_name] = (color_btn, value_label)
            row += 1
    
    def pick_color(self, color_name):
        """Open color picker for a specific color"""
        current_color = self.current_colors[color_name]
        qcolor = QColor(current_color)
        
        color = QColorDialog.getColor(qcolor, self, f"Pick color for {color_name}")
        
        if color.isValid():
            color_hex = color.name()
            self.current_colors[color_name] = color_hex
            
            # Update button and label
            btn, label = self.color_buttons[color_name]
            btn.setStyleSheet(f"background-color: {color_hex}; border: 1px solid #888;")
            label.setText(color_hex)
    
    def duplicate_style(self):
        """Duplicate the selected style with a new name"""
        if not self.current_style_name:
            QMessageBox.warning(self, "Warning", "Please select a style to duplicate")
            return
        
        new_name = self.new_name_input.text().strip()
        if not new_name:
            QMessageBox.warning(self, "Warning", "Please enter a name for the new style")
            return
        
        # BUG FIX 1: Prevent using reserved names
        if new_name.lower() in ['dark', 'light']:
            QMessageBox.warning(
                self, 
                "Reserved Name", 
                f"'{new_name}' is a reserved built-in style name.\n\nPlease choose a different name for your custom style."
            )
            return
        
        # Validate name (alphanumeric + underscore)
        if not new_name.replace('_', '').isalnum():
            QMessageBox.warning(self, "Warning", "Style name must be alphanumeric (underscores allowed)")
            return
        
        # Check if already exists
        custom_dir = Path(__file__).parent / 'custom_styles'
        new_file = custom_dir / f'{new_name}.py'
        if new_file.exists():
            QMessageBox.warning(self, "Warning", f"Style '{new_name}' already exists")
            return
        
        # Create new style file
        self.save_style_to_file(new_name, self.current_colors)
        
        # Reload list and select new style
        self.load_styles_list()
        self.new_name_input.clear()
        
    
    def delete_style(self):
        """Delete the selected custom style"""
        if not self.current_style_name:
            return
        
        # Can't delete built-in styles
        if self.current_style_name in ['dark', 'light']:
            QMessageBox.warning(self, "Warning", "Cannot delete built-in styles")
            return
        
        reply = QMessageBox.question(
            self, 
            "Confirm Delete", 
            f"Delete style '{self.current_style_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            custom_dir = Path(__file__).parent / 'custom_styles'
            file_to_delete = custom_dir / f'{self.current_style_name}.py'
            
            try:
                file_to_delete.unlink()
                self.load_styles_list()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete: {e}")
    
    def save_style_to_file(self, style_name, colors):
        """Save a style to a Python file"""
        custom_dir = Path(__file__).parent / 'custom_styles'
        custom_dir.mkdir(exist_ok=True)
        
        file_path = custom_dir / f'{style_name}.py'
        
        # Generate Python file content
        content = f'''# Custom style: {style_name}
# Auto-generated by Style Editor

COLORS = {{
'''
        for color_name, color_value in colors.items():
            content += f"    '{color_name}': '{color_value}',\n"
        
        content += "}\n\n"
        content += "from pathlib import Path as _Path\n"
        content += "exec((_Path(__file__).parent.parent / 'styles_base_layout.py').read_text(encoding='utf-8'))\n"
        
        # Write to file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def apply_and_close(self):
        """Apply current style and close dialog"""
        if self.current_style_name:
            # If we've modified a custom style, save it
            if self.current_style_name not in ['dark', 'light']:
                self.save_style_to_file(self.current_style_name, self.current_colors)
            
            # Set as current style
            self.config.set_current_style(self.current_style_name)
        
        self.accept()
