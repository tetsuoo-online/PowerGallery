"""
Card Details Dialog - Shows image metadata in a transparent popup
"""

from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPainter, QColor, QPixmap


class CardDetailsDialog(QWidget):
    """
    Transparent popup showing card/image details
    Click anywhere to close
    """
    
    def __init__(self, card, parent=None):
        super().__init__(parent)
        self.card = card
        self.source_json = getattr(card, 'source_json', None)
        
        # Window flags for transparent, frameless, always-on-top popup
        self.setWindowFlags(
            Qt.WindowType.Tool |
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the UI with image details"""
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(8)
        
        # Get file information
        file_path = Path(self.card.image_path)
        
        # Get file stats
        try:
            stats = file_path.stat()
            file_size = self.format_file_size(stats.st_size)
            file_date = datetime.fromtimestamp(stats.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        except Exception:
            file_size = "Unknown"
            file_date = "Unknown"
        
        # Get image resolution
        try:
            pixmap = QPixmap(str(file_path))
            if not pixmap.isNull():
                resolution = f"{pixmap.width()} × {pixmap.height()} px"
            else:
                resolution = "Unknown"
        except Exception:
            resolution = "Unknown"
        
        # Display title is provided by the active module through a common API.
        # No module-specific fallback logic here.
        module_data = getattr(self.card, 'module_data', {}) or {}
        display_title = str(module_data.get('display_title', '')).strip()
        display_title_label = str(module_data.get('display_title_label', '')).strip() or 'Info'

        # Create labels with info
        info_items = []

        if display_title:
            info_items.append((display_title_label, display_title))

        info_items.extend([
            ("Filename", file_path.name),
            ("Resolution", resolution),
            ("Size", file_size),
            ("Modified", file_date),
        ])
        
        # Add source JSON if available
        if self.source_json:
            info_items.append(("Source JSON", self.source_json))
        
        # Add all info labels
        for label_text, value_text in info_items:
            value_text = str(value_text)

            if label_text == "Filename" and len(value_text) > 64:
                value_text = value_text[:64] + "\n" + value_text[64:]

            label = QLabel(f"{label_text}: {value_text}")
            label.setStyleSheet("""
                QLabel {
                    color: white;
                    font-size: 13px;
                    padding: 3px;
                }
            """)
            label.setWordWrap(True)
            layout.addWidget(label)
        
        self.setLayout(layout)
        
        # Adjust size to content
        self.adjustSize()
        self.setMinimumWidth(300)
        self.setMaximumWidth(500)
        
    def format_file_size(self, size_bytes):
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def paintEvent(self, event):
        """Draw semi-transparent rounded background"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw rounded rectangle background with transparency
        painter.setBrush(QColor(30, 30, 30, 230))  # Dark gray with alpha
        painter.setPen(QColor(100, 100, 100, 255))  # Border
        painter.drawRoundedRect(self.rect(), 10, 10)
        
        painter.end()
    
    def mousePressEvent(self, event):
        """Close on any click"""
        self.close()
    
    def closeEvent(self, event):
        """Clear reference in grid_tab when closing"""
        if self.card:
            widget = self.card.parent()
            while widget:
                if widget.__class__.__name__ == 'GridTab':
                    if hasattr(widget, 'active_details_dialog') and widget.active_details_dialog is self:
                        widget.active_details_dialog = None
                    break
                widget = widget.parent() if hasattr(widget, 'parent') else None
        
        super().closeEvent(event)
    
    def show_near_card(self):
        """Position the dialog near the card"""
        if self.card and self.card.window():
            card_global_pos = self.card.mapToGlobal(QPoint(0, 0))
            
            x = card_global_pos.x() + self.card.width() + 10
            y = card_global_pos.y()
            
            screen_geometry = self.screen().geometry()
            if x + self.width() > screen_geometry.right():
                x = card_global_pos.x() - self.width() - 10
            
            if y + self.height() > screen_geometry.bottom():
                y = screen_geometry.bottom() - self.height() - 10
            
            x = max(10, x)
            y = max(10, y)
            
            self.move(x, y)
        
        self.show()
