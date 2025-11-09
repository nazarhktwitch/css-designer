#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import json
import copy
import re
import os
from typing import Dict, List, Optional, Any
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QSplitter, QTreeWidget, QTreeWidgetItem, QTextEdit, QPushButton,
    QLabel, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QColorDialog,
    QGroupBox, QFormLayout, QScrollArea, QFileDialog, QMessageBox,
    QToolBar, QMenuBar, QStatusBar, QTabWidget, QListWidget, QListWidgetItem,
    QGraphicsView, QGraphicsScene, QGraphicsRectItem, QGraphicsItem,
    QGraphicsTextItem, QFrame, QCheckBox, QSlider, QInputDialog, QMenu
)
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal, QObject, QSize, QTimer
from PyQt6.QtGui import (
    QColor, QFont, QTextCharFormat, QSyntaxHighlighter, QTextDocument,
    QAction, QIcon, QKeySequence, QPalette, QPainter, QBrush, QPen,
    QTextCursor
)

# Optional WebEngine import
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    HAS_WEBENGINE = True
except ImportError:
    HAS_WEBENGINE = False
    from PyQt6.QtWidgets import QTextBrowser
    QWebEngineView = QTextBrowser

from localization import Localization

class CSSHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_rules()
    
    def setup_rules(self):
        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor("#0000FF"))
        keyword_format.setFontWeight(700)
        
        property_format = QTextCharFormat()
        property_format.setForeground(QColor("#008000"))
        
        value_format = QTextCharFormat()
        value_format.setForeground(QColor("#800080"))
        
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#808080"))
        comment_format.setFontItalic(True)
        
        self.rules = [
            (r'\b(?:margin|padding|width|height|color|background|border|font|display|position|flex|grid)\b', property_format),
            (r'\b(?:px|em|rem|%|vh|vw|auto|none|block|inline|flex|grid|absolute|relative|fixed|static)\b', value_format),
            (r'#[0-9A-Fa-f]{3,6}', value_format),
            (r'//.*', comment_format),
            (r'/\*.*\*/', comment_format),
        ]
    
    def highlightBlock(self, text):
        for pattern, format in self.rules:
            for match in re.finditer(pattern, text):
                self.setFormat(match.start(), match.end() - match.start(), format)

class HTMLHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_rules()
    
    def setup_rules(self):
        tag_format = QTextCharFormat()
        tag_format.setForeground(QColor("#0000FF"))
        tag_format.setFontWeight(700)
        
        attribute_format = QTextCharFormat()
        attribute_format.setForeground(QColor("#008000"))
        
        value_format = QTextCharFormat()
        value_format.setForeground(QColor("#800080"))
        
        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor("#808080"))
        comment_format.setFontItalic(True)
        
        self.rules = [
            (r'<!--.*?-->', comment_format),
            (r'<[!?]?/?\w+', tag_format),
            (r'\b(?:id|class|style|href|src|alt|title|type|name|value|placeholder|required|disabled)\s*=', attribute_format),
            (r'"[^"]*"', value_format),
            (r"'[^']*'", value_format),
        ]
    
    def highlightBlock(self, text):
        for pattern, format in self.rules:
            for match in re.finditer(pattern, text, re.MULTILINE | re.DOTALL):
                self.setFormat(match.start(), match.end() - match.start(), format)

def validate_html(html_text):
    """Validate HTML structure and return list of errors"""
    errors = []
    if not html_text.strip():
        return errors
    
    # Check for unclosed tags
    open_tags = []
    tag_pattern = r'<(/?)([a-zA-Z][a-zA-Z0-9]*)[^>]*>'
    
    for match in re.finditer(tag_pattern, html_text):
        is_closing = match.group(1) == '/'
        tag_name = match.group(2).lower()
        
        # Skip self-closing tags
        if tag_name in ['br', 'hr', 'img', 'input', 'meta', 'link', 'area', 'base', 'col', 'embed', 'source', 'track', 'wbr']:
            continue
        
        if is_closing:
            if not open_tags or open_tags[-1] != tag_name:
                if open_tags:
                    errors.append(f"Unclosed tag: <{open_tags[-1]}>")
                else:
                    errors.append(f"Unexpected closing tag: </{tag_name}>")
            else:
                open_tags.pop()
        else:
            open_tags.append(tag_name)
    
    # Check for remaining unclosed tags
    for tag in open_tags:
        errors.append(f"Unclosed tag: <{tag}>")
    
    return errors

class DraggableRectItem(QGraphicsRectItem):
    def __init__(self, rect, element_name="div", parent=None):
        super().__init__(rect, parent)
        self.element_name = element_name
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsFocusable, True)
        self.setAcceptHoverEvents(True)
        
        self.styles = {
            'width': f'{int(rect.width())}px',
            'height': f'{int(rect.height())}px',
            'background-color': '#e0e0e0',
            'border': '1px solid #ccc',
            'position': 'absolute',
            'left': f'{int(rect.x())}px',
            'top': f'{int(rect.y())}px'
        }
        
        self.text_content = ""
        self.text_item = None
        self.update_appearance()
    
    def update_appearance(self):
        color = QColor(self.styles.get('background-color', '#e0e0e0'))
        border_color = QColor('#ccc')
        
        if 'border-color' in self.styles:
            border_color = QColor(self.styles['border-color'])
        
        self.setBrush(QBrush(color))
        self.setPen(QPen(border_color, 2))
        
        if self.text_item:
            self.text_item.setPlainText(self.text_content)
            font_size = int(self.styles.get('font-size', '14px').replace('px', ''))
            font_family = self.styles.get('font-family', 'Arial')
            self.text_item.setFont(QFont(font_family, font_size))
            text_color = QColor(self.styles.get('color', '#000000'))
            self.text_item.setDefaultTextColor(text_color)
            self.text_item.setPos(self.rect().x() + 5, self.rect().y() + 5)
    
    def set_text(self, text):
        self.text_content = text
        if not self.text_item:
            self.text_item = QGraphicsTextItem(text, self)
        else:
            self.text_item.setPlainText(text)
        self.update_appearance()
    
    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            pos = self.pos()
            # Apply snap-to-grid if enabled
            if hasattr(self.scene(), 'views') and self.scene().views():
                view = self.scene().views()[0]
                if hasattr(view, 'snap_to_grid') and view.snap_to_grid:
                    grid_size = view.grid_size
                    snapped_x = round(pos.x() / grid_size) * grid_size
                    snapped_y = round(pos.y() / grid_size) * grid_size
                    if snapped_x != pos.x() or snapped_y != pos.y():
                        self.setPos(snapped_x, snapped_y)
                        pos = self.pos()
            self.styles['left'] = f'{int(pos.x())}px'
            self.styles['top'] = f'{int(pos.y())}px'
            if self.text_item:
                self.text_item.setPos(self.rect().x() + 5, self.rect().y() + 5)
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            if value:
                pen = QPen(QColor("#0078d4"), 3)
                self.setPen(pen)
            else:
                border_color = QColor('#ccc')
                if 'border-color' in self.styles:
                    border_color = QColor(self.styles['border-color'])
                self.setPen(QPen(border_color, 2))
        return super().itemChange(change, value)
    
    def setRect(self, *args):
        if len(args) == 1:
            rect = args[0]
            super().setRect(rect)
        else:
            super().setRect(*args)
            rect = QRectF(*args)
        
        if hasattr(self, 'styles'):
            current_rect = self.rect()
            self.styles['width'] = f'{int(current_rect.width())}px'
            self.styles['height'] = f'{int(current_rect.height())}px'
            if self.text_item:
                self.text_item.setPos(current_rect.x() + 5, current_rect.y() + 5)
    
    def set_style(self, property_name, value):
        self.styles[property_name] = value
        
        if property_name in ['width', 'height']:
            if 'px' in str(value):
                size = int(str(value).replace('px', ''))
                current_rect = self.rect()
                if property_name == 'width':
                    super().setRect(current_rect.x(), current_rect.y(), size, current_rect.height())
                else:
                    super().setRect(current_rect.x(), current_rect.y(), current_rect.width(), size)
                self.styles['width'] = f'{int(self.rect().width())}px'
                self.styles['height'] = f'{int(self.rect().height())}px'
                if self.text_item:
                    self.text_item.setPos(self.rect().x() + 5, self.rect().y() + 5)
        
        self.update_appearance()
    
    def get_css(self, element_index=0):
        pos = self.pos()
        css = f".{self.element_name.lower()}-element-{element_index} {{\n"
        for prop, value in self.styles.items():
            if prop == 'left':
                css += f"    left: {int(pos.x())}px;\n"
            elif prop == 'top':
                css += f"    top: {int(pos.y())}px;\n"
            else:
                css += f"    {prop}: {value};\n"
        css += "}\n"
        return css

class VisualEditor(QGraphicsView):
    element_selected = pyqtSignal(object)
    element_changed = pyqtSignal()
    delete_requested = pyqtSignal(object)
    duplicate_requested = pyqtSignal(object)
    copy_requested = pyqtSignal(object)
    paste_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        self.elements = []
        self.selected_element = None
        self.snap_to_grid = False
        self.grid_size = 10  # Default grid size in pixels
        self.show_grid = False  # Show grid visualization
        
        self.setBackgroundBrush(QBrush(QColor("#f5f5f5")))
    
    def drawBackground(self, painter, rect):
        """Override to draw grid"""
        super().drawBackground(painter, rect)
        
        if self.show_grid:
            painter.setPen(QPen(QColor("#d0d0d0"), 1, Qt.PenStyle.DotLine))
            
            # Draw vertical lines
            left = int(rect.left()) - (int(rect.left()) % self.grid_size)
            x = left
            while x < rect.right():
                painter.drawLine(int(x), int(rect.top()), int(x), int(rect.bottom()))
                x += self.grid_size
            
            # Draw horizontal lines
            top = int(rect.top()) - (int(rect.top()) % self.grid_size)
            y = top
            while y < rect.bottom():
                painter.drawLine(int(rect.left()), int(y), int(rect.right()), int(y))
                y += self.grid_size
    
    def add_element(self, element_type="div", x=50, y=50, width=200, height=100):
        rect = QRectF(x, y, width, height)
        item = DraggableRectItem(rect, element_type)
        self.scene.addItem(item)
        self.elements.append(item)
        
        item.setSelected(True)
        if self.selected_element:
            self.selected_element.setSelected(False)
        self.selected_element = item
        self.element_selected.emit(item)
        self.element_changed.emit()
        
        return item
    
    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        
        item = self.itemAt(event.pos())
        if item and isinstance(item, DraggableRectItem):
            if self.selected_element:
                self.selected_element.setSelected(False)
            self.selected_element = item
            item.setSelected(True)
            self.element_selected.emit(item)
    
    def contextMenuEvent(self, event):
        """Context menu for elements"""
        item = self.itemAt(event.pos())
        if item and isinstance(item, DraggableRectItem):
            parent_app = self.parent()
            while parent_app and not hasattr(parent_app, 'localization'):
                parent_app = parent_app.parent()
            
            menu = QMenu(self)
            if parent_app and hasattr(parent_app, 'localization'):
                localization = parent_app.localization
            else:
                from localization import Localization
                localization = Localization()
            
            delete_action = QAction(localization.tr("edit_delete", "Delete"), self)
            delete_action.setShortcut(QKeySequence("Delete"))
            delete_action.triggered.connect(lambda: self.delete_requested.emit(item))
            menu.addAction(delete_action)
            
            duplicate_action = QAction(localization.tr("edit_duplicate", "Duplicate"), self)
            duplicate_action.setShortcut(QKeySequence("Ctrl+D"))
            duplicate_action.triggered.connect(lambda: self.duplicate_requested.emit(item))
            menu.addAction(duplicate_action)
            
            menu.addSeparator()
            
            copy_action = QAction(localization.tr("edit_copy", "Copy"), self)
            copy_action.setShortcut(QKeySequence("Ctrl+C"))
            copy_action.triggered.connect(lambda: self.copy_requested.emit(item))
            menu.addAction(copy_action)
            
            paste_action = QAction(localization.tr("edit_paste", "Paste"), self)
            paste_action.setShortcut(QKeySequence("Ctrl+V"))
            paste_action.triggered.connect(lambda: self.paste_requested.emit())
            menu.addAction(paste_action)
            
            menu.exec(event.globalPos())
    
    def mouseMoveEvent(self, event):
        super().mouseMoveEvent(event)
        if self.selected_element and event.buttons() == Qt.MouseButton.LeftButton:
            self.element_changed.emit()
    
    def mouseReleaseEvent(self, event):
        super().mouseReleaseEvent(event)
        if self.selected_element:
            self.element_changed.emit()
    
    def get_all_css(self):
        css = ""
        for i, element in enumerate(self.elements):
            css += element.get_css(i) + "\n"
        return css

# Properties
class PropertiesPanel(QWidget):
    style_changed = pyqtSignal(str, str)
    text_changed = pyqtSignal(str)
    
    def __init__(self, localization=None, parent=None):
        super().__init__(parent)
        self.localization = localization or Localization()
        self.current_element = None
        self.updating = False
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout()
        scroll_widget.setLayout(scroll_layout)
        
        # Text content
        text_group = QGroupBox(self.localization.tr("property_text_content", "Text Content"))
        text_group.setProperty("loc_key", "property_text_content")
        text_layout = QVBoxLayout()
        self.text_edit = QLineEdit()
        self.text_edit.textChanged.connect(self.on_text_changed)
        text_layout.addWidget(self.text_edit)
        text_group.setLayout(text_layout)
        scroll_layout.addWidget(text_group)
        
        # Layout properties
        layout_group = QGroupBox(self.localization.tr("panel_layout", "Layout"))
        layout_group.setProperty("loc_key", "panel_layout")
        layout_form = QFormLayout()
        
        self.display_combo = QComboBox()
        self.display_combo.addItems(["block", "inline", "inline-block", "flex", "grid", "none"])
        self.display_combo.currentTextChanged.connect(lambda v: self.on_property_changed("display", v))
        display_label = QLabel(self.localization.tr("property_display", "Display") + ":")
        display_label.setProperty("loc_key", "property_display")
        layout_form.addRow(display_label, self.display_combo)
        
        self.position_combo = QComboBox()
        self.position_combo.addItems(["static", "relative", "absolute", "fixed", "sticky"])
        self.position_combo.currentTextChanged.connect(lambda v: self.on_property_changed("position", v))
        position_label = QLabel(self.localization.tr("property_position", "Position") + ":")
        position_label.setProperty("loc_key", "property_position")
        layout_form.addRow(position_label, self.position_combo)
        
        # Flexbox properties
        self.flex_direction_combo = QComboBox()
        self.flex_direction_combo.addItems(["row", "row-reverse", "column", "column-reverse"])
        self.flex_direction_combo.currentTextChanged.connect(lambda v: self.on_property_changed("flex-direction", v))
        flex_dir_label = QLabel(self.localization.tr("property_flex_direction", "Flex Direction") + ":")
        flex_dir_label.setProperty("loc_key", "property_flex_direction")
        layout_form.addRow(flex_dir_label, self.flex_direction_combo)
        
        self.flex_wrap_combo = QComboBox()
        self.flex_wrap_combo.addItems(["nowrap", "wrap", "wrap-reverse"])
        self.flex_wrap_combo.currentTextChanged.connect(lambda v: self.on_property_changed("flex-wrap", v))
        flex_wrap_label = QLabel(self.localization.tr("property_flex_wrap", "Flex Wrap") + ":")
        flex_wrap_label.setProperty("loc_key", "property_flex_wrap")
        layout_form.addRow(flex_wrap_label, self.flex_wrap_combo)
        
        self.justify_content_combo = QComboBox()
        self.justify_content_combo.addItems(["flex-start", "flex-end", "center", "space-between", "space-around", "space-evenly"])
        self.justify_content_combo.currentTextChanged.connect(lambda v: self.on_property_changed("justify-content", v))
        justify_label = QLabel(self.localization.tr("property_justify_content", "Justify Content") + ":")
        justify_label.setProperty("loc_key", "property_justify_content")
        layout_form.addRow(justify_label, self.justify_content_combo)
        
        self.align_items_combo = QComboBox()
        self.align_items_combo.addItems(["stretch", "flex-start", "flex-end", "center", "baseline"])
        self.align_items_combo.currentTextChanged.connect(lambda v: self.on_property_changed("align-items", v))
        align_items_label = QLabel(self.localization.tr("property_align_items", "Align Items") + ":")
        align_items_label.setProperty("loc_key", "property_align_items")
        layout_form.addRow(align_items_label, self.align_items_combo)
        
        # Grid properties
        self.grid_template_columns = QLineEdit()
        self.grid_template_columns.setPlaceholderText("1fr 1fr 1fr")
        self.grid_template_columns.textChanged.connect(lambda v: self.on_property_changed("grid-template-columns", v))
        grid_cols_label = QLabel(self.localization.tr("property_grid_template_columns", "Grid Template Columns") + ":")
        grid_cols_label.setProperty("loc_key", "property_grid_template_columns")
        layout_form.addRow(grid_cols_label, self.grid_template_columns)
        
        self.grid_template_rows = QLineEdit()
        self.grid_template_rows.setPlaceholderText("auto auto")
        self.grid_template_rows.textChanged.connect(lambda v: self.on_property_changed("grid-template-rows", v))
        grid_rows_label = QLabel(self.localization.tr("property_grid_template_rows", "Grid Template Rows") + ":")
        grid_rows_label.setProperty("loc_key", "property_grid_template_rows")
        layout_form.addRow(grid_rows_label, self.grid_template_rows)
        
        self.grid_gap = QLineEdit()
        self.grid_gap.setPlaceholderText("10px")
        self.grid_gap.textChanged.connect(lambda v: self.on_property_changed("gap", v))
        grid_gap_label = QLabel(self.localization.tr("property_gap", "Gap") + ":")
        grid_gap_label.setProperty("loc_key", "property_gap")
        layout_form.addRow(grid_gap_label, self.grid_gap)
        
        layout_group.setLayout(layout_form)
        scroll_layout.addWidget(layout_group)
        
        # Sizing
        size_group = QGroupBox(self.localization.tr("panel_sizing", "Sizing"))
        size_group.setProperty("loc_key", "panel_sizing")
        size_form = QFormLayout()
        
        self.width_spin = QSpinBox()
        self.width_spin.setRange(0, 10000)
        self.width_spin.setSuffix(" px")
        self.width_spin.valueChanged.connect(lambda v: self.on_property_changed("width", f"{v}px"))
        width_label = QLabel(self.localization.tr("property_width", "Width") + ":")
        width_label.setProperty("loc_key", "property_width")
        size_form.addRow(width_label, self.width_spin)
        
        self.height_spin = QSpinBox()
        self.height_spin.setRange(0, 10000)
        self.height_spin.setSuffix(" px")
        self.height_spin.valueChanged.connect(lambda v: self.on_property_changed("height", f"{v}px"))
        height_label = QLabel(self.localization.tr("property_height", "Height") + ":")
        height_label.setProperty("loc_key", "property_height")
        size_form.addRow(height_label, self.height_spin)
        
        size_group.setLayout(size_form)
        scroll_layout.addWidget(size_group)
        
        # Spacing
        spacing_group = QGroupBox(self.localization.tr("panel_spacing", "Spacing"))
        spacing_form = QFormLayout()
        
        self.margin_top = QSpinBox()
        self.margin_top.setRange(-1000, 1000)
        self.margin_top.setSuffix(" px")
        self.margin_top.valueChanged.connect(self.update_margin)
        spacing_form.addRow(self.localization.tr("property_margin_top", "Margin Top") + ":", self.margin_top)
        
        self.margin_right = QSpinBox()
        self.margin_right.setRange(-1000, 1000)
        self.margin_right.setSuffix(" px")
        self.margin_right.valueChanged.connect(self.update_margin)
        spacing_form.addRow(self.localization.tr("property_margin_right", "Margin Right") + ":", self.margin_right)
        
        self.margin_bottom = QSpinBox()
        self.margin_bottom.setRange(-1000, 1000)
        self.margin_bottom.setSuffix(" px")
        self.margin_bottom.valueChanged.connect(self.update_margin)
        spacing_form.addRow(self.localization.tr("property_margin_bottom", "Margin Bottom") + ":", self.margin_bottom)
        
        self.margin_left = QSpinBox()
        self.margin_left.setRange(-1000, 1000)
        self.margin_left.setSuffix(" px")
        self.margin_left.valueChanged.connect(self.update_margin)
        spacing_form.addRow(self.localization.tr("property_margin_left", "Margin Left") + ":", self.margin_left)
        
        self.padding_top = QSpinBox()
        self.padding_top.setRange(0, 1000)
        self.padding_top.setSuffix(" px")
        self.padding_top.valueChanged.connect(self.update_padding)
        spacing_form.addRow(self.localization.tr("property_padding_top", "Padding Top") + ":", self.padding_top)
        
        self.padding_right = QSpinBox()
        self.padding_right.setRange(0, 1000)
        self.padding_right.setSuffix(" px")
        self.padding_right.valueChanged.connect(self.update_padding)
        spacing_form.addRow(self.localization.tr("property_padding_right", "Padding Right") + ":", self.padding_right)
        
        self.padding_bottom = QSpinBox()
        self.padding_bottom.setRange(0, 1000)
        self.padding_bottom.setSuffix(" px")
        self.padding_bottom.valueChanged.connect(self.update_padding)
        spacing_form.addRow(self.localization.tr("property_padding_bottom", "Padding Bottom") + ":", self.padding_bottom)
        
        self.padding_left = QSpinBox()
        self.padding_left.setRange(0, 1000)
        self.padding_left.setSuffix(" px")
        self.padding_left.valueChanged.connect(self.update_padding)
        spacing_form.addRow(self.localization.tr("property_padding_left", "Padding Left") + ":", self.padding_left)
        
        spacing_group.setLayout(spacing_form)
        scroll_layout.addWidget(spacing_group)
        
        # Colors
        color_group = QGroupBox(self.localization.tr("panel_colors", "Colors"))
        color_form = QFormLayout()
        
        self.bg_color_btn = QPushButton(self.localization.tr("button_choose_color", "Choose Color"))
        self.bg_color_btn.clicked.connect(lambda: self.choose_color("background-color"))
        color_form.addRow(self.localization.tr("property_background", "Background") + ":", self.bg_color_btn)
        
        self.text_color_btn = QPushButton(self.localization.tr("button_choose_color", "Choose Color"))
        self.text_color_btn.clicked.connect(lambda: self.choose_color("color"))
        color_form.addRow(self.localization.tr("property_text_color", "Text Color") + ":", self.text_color_btn)
        
        self.border_color_btn = QPushButton(self.localization.tr("button_choose_color", "Choose Color"))
        self.border_color_btn.clicked.connect(lambda: self.choose_color("border-color"))
        color_form.addRow(self.localization.tr("property_border_color", "Border Color") + ":", self.border_color_btn)
        
        color_group.setLayout(color_form)
        scroll_layout.addWidget(color_group)
        
        # Typography
        font_group = QGroupBox(self.localization.tr("panel_typography", "Typography"))
        font_form = QFormLayout()
        
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 200)
        self.font_size.setSuffix(" px")
        self.font_size.valueChanged.connect(lambda v: self.on_property_changed("font-size", f"{v}px"))
        font_form.addRow(self.localization.tr("property_font_size", "Font Size") + ":", self.font_size)
        
        self.font_family = QComboBox()
        self.font_family.addItems(["Arial", "Helvetica", "Times New Roman", "Courier New", "Verdana", "Georgia", "sans-serif", "serif", "monospace"])
        self.font_family.currentTextChanged.connect(lambda v: self.on_property_changed("font-family", v))
        font_form.addRow(self.localization.tr("property_font_family", "Font Family") + ":", self.font_family)
        
        self.font_weight = QComboBox()
        self.font_weight.addItems(["normal", "bold", "100", "200", "300", "400", "500", "600", "700", "800", "900"])
        self.font_weight.currentTextChanged.connect(lambda v: self.on_property_changed("font-weight", v))
        font_form.addRow(self.localization.tr("property_font_weight", "Font Weight") + ":", self.font_weight)
        
        self.text_align = QComboBox()
        self.text_align.addItems(["left", "center", "right", "justify"])
        self.text_align.currentTextChanged.connect(lambda v: self.on_property_changed("text-align", v))
        font_form.addRow(self.localization.tr("property_text_align", "Text Align") + ":", self.text_align)
        
        font_group.setLayout(font_form)
        scroll_layout.addWidget(font_group)
        
        # Borders
        border_group = QGroupBox(self.localization.tr("panel_borders", "Borders"))
        border_form = QFormLayout()
        
        self.border_width = QSpinBox()
        self.border_width.setRange(0, 50)
        self.border_width.setSuffix(" px")
        self.border_width.valueChanged.connect(self.update_border)
        border_form.addRow(self.localization.tr("property_border_width", "Border Width") + ":", self.border_width)
        
        self.border_style = QComboBox()
        self.border_style.addItems(["none", "solid", "dashed", "dotted", "double", "groove", "ridge", "inset", "outset"])
        self.border_style.currentTextChanged.connect(self.update_border)
        border_form.addRow(self.localization.tr("property_border_style", "Border Style") + ":", self.border_style)
        
        self.border_radius = QSpinBox()
        self.border_radius.setRange(0, 500)
        self.border_radius.setSuffix(" px")
        self.border_radius.valueChanged.connect(lambda v: self.on_property_changed("border-radius", f"{v}px"))
        border_form.addRow(self.localization.tr("property_border_radius", "Border Radius") + ":", self.border_radius)
        
        border_group.setLayout(border_form)
        scroll_layout.addWidget(border_group)
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        layout.addStretch()
    
    def on_property_changed(self, property_name, value):
        if not self.updating and self.current_element:
            self.current_element.set_style(property_name, value)
            self.style_changed.emit(property_name, value)
    
    def on_text_changed(self, text):
        if not self.updating and self.current_element:
            self.current_element.set_text(text)
            self.text_changed.emit(text)
    
    def update_margin(self):
        margin = f"{self.margin_top.value()}px {self.margin_right.value()}px {self.margin_bottom.value()}px {self.margin_left.value()}px"
        self.on_property_changed("margin", margin)
    
    def update_padding(self):
        padding = f"{self.padding_top.value()}px {self.padding_right.value()}px {self.padding_bottom.value()}px {self.padding_left.value()}px"
        self.on_property_changed("padding", padding)
    
    def update_border(self):
        border = f"{self.border_width.value()}px {self.border_style.currentText()}"
        if self.current_element and 'border-color' in self.current_element.styles:
            border += f" {self.current_element.styles.get('border-color', '#000')}"
        self.on_property_changed("border", border)
    
    def choose_color(self, property_name):
        if not self.current_element:
            return
        
        current_color = self.current_element.styles.get(property_name, "#000000")
        color = QColorDialog.getColor(QColor(current_color), self, f"Choose {property_name}")
        if color.isValid():
            color_str = color.name()
            self.on_property_changed(property_name, color_str)
            
            if property_name == "background-color":
                self.bg_color_btn.setText(color_str)
            elif property_name == "color":
                self.text_color_btn.setText(color_str)
            elif property_name == "border-color":
                self.border_color_btn.setText(color_str)
    
    def set_element(self, element):
        self.updating = True
        self.current_element = element
        
        if not element:
            self.updating = False
            return
        
        styles = element.styles
        
        if 'display' in styles:
            idx = self.display_combo.findText(styles['display'])
            if idx >= 0:
                self.display_combo.setCurrentIndex(idx)
        
        if 'position' in styles:
            idx = self.position_combo.findText(styles['position'])
            if idx >= 0:
                self.position_combo.setCurrentIndex(idx)
        
        # Flexbox properties
        if 'flex-direction' in styles:
            idx = self.flex_direction_combo.findText(styles['flex-direction'])
            if idx >= 0:
                self.flex_direction_combo.setCurrentIndex(idx)
        
        if 'flex-wrap' in styles:
            idx = self.flex_wrap_combo.findText(styles['flex-wrap'])
            if idx >= 0:
                self.flex_wrap_combo.setCurrentIndex(idx)
        
        if 'justify-content' in styles:
            idx = self.justify_content_combo.findText(styles['justify-content'])
            if idx >= 0:
                self.justify_content_combo.setCurrentIndex(idx)
        
        if 'align-items' in styles:
            idx = self.align_items_combo.findText(styles['align-items'])
            if idx >= 0:
                self.align_items_combo.setCurrentIndex(idx)
        
        # Grid properties
        if 'grid-template-columns' in styles:
            self.grid_template_columns.setText(styles['grid-template-columns'])
        
        if 'grid-template-rows' in styles:
            self.grid_template_rows.setText(styles['grid-template-rows'])
        
        if 'gap' in styles:
            self.grid_gap.setText(styles['gap'])
        
        if 'width' in styles:
            width = int(styles['width'].replace('px', ''))
            self.width_spin.setValue(width)
        
        if 'height' in styles:
            height = int(styles['height'].replace('px', ''))
            self.height_spin.setValue(height)
        
        if 'background-color' in styles:
            self.bg_color_btn.setText(styles['background-color'])
        
        if 'color' in styles:
            self.text_color_btn.setText(styles.get('color', '#000000'))
        
        if 'border-color' in styles:
            self.border_color_btn.setText(styles['border-color'])
        
        if hasattr(element, 'text_content'):
            self.text_edit.setText(element.text_content)
        
        self.updating = False
    
    def update_language(self, localization):
        self.localization = localization
        # Update widgets
        for widget in self.findChildren(QWidget):
            loc_key = widget.property("loc_key")
            if loc_key:
                if isinstance(widget, QGroupBox):
                    widget.setTitle(self.localization.tr(loc_key, ""))
                elif isinstance(widget, QLabel):
                    widget.setText(self.localization.tr(loc_key, "") + (":" if "property" in loc_key else ""))
                elif isinstance(widget, QPushButton):
                    # Only update if button shows default text (not a color value)
                    btn_text = widget.text()
                    if btn_text in ["Choose Color", "Выбрать цвет"] or (not btn_text.startswith("#") and len(btn_text) < 20):
                        widget.setText(self.localization.tr(loc_key, ""))
        
        # Also update labels in form layouts that don't have loc_key yet (backward compatibility)
        label_map = {
            "Display": "property_display",
            "Position": "property_position",
            "Width": "property_width",
            "Height": "property_height",
            "Margin Top": "property_margin_top",
            "Margin Right": "property_margin_right",
            "Margin Bottom": "property_margin_bottom",
            "Margin Left": "property_margin_left",
            "Padding Top": "property_padding_top",
            "Padding Right": "property_padding_right",
            "Padding Bottom": "property_padding_bottom",
            "Padding Left": "property_padding_left",
            "Background": "property_background",
            "Text Color": "property_text_color",
            "Border Color": "property_border_color",
            "Font Size": "property_font_size",
            "Font Family": "property_font_family",
            "Font Weight": "property_font_weight",
            "Text Align": "property_text_align",
            "Border Width": "property_border_width",
            "Border Style": "property_border_style",
            "Border Radius": "property_border_radius"
        }
        
        for widget in self.findChildren(QFormLayout):
            for i in range(widget.rowCount()):
                label = widget.itemAt(i, QFormLayout.ItemRole.LabelRole)
                if label and label.widget():
                    label_widget = label.widget()
                    if isinstance(label_widget, QLabel):
                        # Skip if already has loc_key
                        if label_widget.property("loc_key"):
                            continue
                        text = label_widget.text()
                        if ":" in text:
                            label_text = text.split(":")[0].strip()
                            if label_text in label_map:
                                new_text = self.localization.tr(label_map[label_text], label_text)
                                label_widget.setText(new_text + ":")

class CSSDesignerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.localization = Localization("en")
        self.current_language = "en"
        
        self.project_data = {
            "name": "New Project",
            "components": [],
            "history": [],
            "templates": [],
            "html_content": ""
        }
        self.history_index = -1
        self.html_content = ""
        self.code_update_blocked = False
        self.preview_bg_color = "#000000"  # Default black background
        
        self.setup_ui()
        self.setup_menu()
        self.setup_toolbar()
        
        # Timer for delayed code updates to prevent infinite loops
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.timeout.connect(self.update_code_editor)
        
        # Timer for delayed state saves
        self.save_timer = QTimer()
        self.save_timer.setSingleShot(True)
        self.save_timer.timeout.connect(self.save_state)
    
    def setup_ui(self):
        self.setWindowTitle(self.localization.tr("app_name", "CSS Designer"))
        self.setGeometry(100, 100, 1400, 900)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # Left panel
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(250)
        
        self.components_tree = QTreeWidget()
        self.components_tree.setHeaderLabel(self.localization.tr("panel_components", "Components"))
        self.components_tree.setProperty("loc_key", "panel_components")
        self.components_tree.itemClicked.connect(self.on_component_selected)
        components_label = QLabel(self.localization.tr("panel_components", "Components") + ":")
        components_label.setProperty("loc_key", "panel_components")
        left_layout.addWidget(components_label)
        left_layout.addWidget(self.components_tree)
        
        btn_layout = QHBoxLayout()
        self.add_component_btn = QPushButton(self.localization.tr("panel_add_component", "Add"))
        self.add_component_btn.setProperty("loc_key", "panel_add_component")
        self.add_component_btn.clicked.connect(self.add_component)
        self.remove_component_btn = QPushButton(self.localization.tr("panel_remove_component", "Remove"))
        self.remove_component_btn.setProperty("loc_key", "panel_remove_component")
        self.remove_component_btn.clicked.connect(self.remove_component)
        btn_layout.addWidget(self.add_component_btn)
        btn_layout.addWidget(self.remove_component_btn)
        left_layout.addLayout(btn_layout)
        
        media_label = QLabel(self.localization.tr("panel_media_queries", "Media Queries") + ":")
        media_label.setProperty("loc_key", "panel_media_queries")
        left_layout.addWidget(media_label)
        self.media_queries_list = QListWidget()
        left_layout.addWidget(self.media_queries_list)
        
        media_btn_layout = QHBoxLayout()
        self.add_media_btn = QPushButton(self.localization.tr("panel_add_media", "Add"))
        self.add_media_btn.setProperty("loc_key", "panel_add_media")
        self.add_media_btn.clicked.connect(self.add_media_query)
        media_btn_layout.addWidget(self.add_media_btn)
        
        self.remove_media_btn = QPushButton(self.localization.tr("panel_remove_media", "Remove"))
        self.remove_media_btn.setProperty("loc_key", "panel_remove_media")
        self.remove_media_btn.clicked.connect(self.remove_media_query)
        media_btn_layout.addWidget(self.remove_media_btn)
        left_layout.addLayout(media_btn_layout)
        
        left_layout.addStretch()
        main_splitter.addWidget(left_panel)
        
        # Center area
        center_splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.visual_editor = VisualEditor()
        self.visual_editor.element_selected.connect(self.on_element_selected)
        self.visual_editor.element_changed.connect(self.on_element_visual_changed)
        self.visual_editor.delete_requested.connect(self.delete_element)
        self.visual_editor.duplicate_requested.connect(self.duplicate_element)
        self.visual_editor.copy_requested.connect(self.copy_element)
        self.visual_editor.paste_requested.connect(self.paste_element)
        center_splitter.addWidget(self.visual_editor)
        
        code_tab = QWidget()
        code_layout = QVBoxLayout()
        code_tab.setLayout(code_layout)
        
        code_label = QLabel(self.localization.tr("code_editor_title", "CSS Code") + ":")
        code_label.setProperty("loc_key", "code_editor_title")
        code_layout.addWidget(code_label)
        self.code_editor = QTextEdit()
        self.code_editor.setFont(QFont("Courier", 10))
        self.highlighter = CSSHighlighter(self.code_editor.document())
        self.code_editor.textChanged.connect(self.on_code_changed)
        code_layout.addWidget(self.code_editor)
        
        preview_layout = QHBoxLayout()
        self.preview_web = QWebEngineView()
        self.update_preview()
        preview_layout.addWidget(self.preview_web)
        code_layout.addLayout(preview_layout)
        
        center_splitter.addWidget(code_tab)
        center_splitter.setSizes([400, 300])
        
        main_splitter.addWidget(center_splitter)
        
        # Right panel
        self.properties_panel = PropertiesPanel(self.localization)
        self.properties_panel.style_changed.connect(self.on_style_changed)
        self.properties_panel.text_changed.connect(self.on_text_changed)
        self.properties_panel.setMaximumWidth(300)
        main_splitter.addWidget(self.properties_panel)
        
        main_splitter.setSizes([250, 800, 300])
        
        self.statusBar().showMessage(self.localization.tr("status_ready", "Ready"))
    
    def setup_menu(self):
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu(self.localization.tr("menu_file", "File"))
        file_menu.setProperty("loc_key", "menu_file")
        
        new_action = QAction(self.localization.tr("file_new", "New Project"), self)
        new_action.setProperty("loc_key", "file_new")
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction(self.localization.tr("file_open", "Open"), self)
        open_action.setProperty("loc_key", "file_open")
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)
        
        open_html_action = QAction(self.localization.tr("file_open_html", "Open HTML"), self)
        open_html_action.setProperty("loc_key", "file_open_html")
        open_html_action.triggered.connect(self.open_html)
        file_menu.addAction(open_html_action)
        
        edit_html_action = QAction(self.localization.tr("file_edit_html", "Edit HTML"), self)
        edit_html_action.setProperty("loc_key", "file_edit_html")
        edit_html_action.triggered.connect(self.edit_html)
        file_menu.addAction(edit_html_action)
        
        save_action = QAction(self.localization.tr("file_save", "Save"), self)
        save_action.setProperty("loc_key", "file_save")
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        export_menu = file_menu.addMenu(self.localization.tr("file_export", "Export"))
        export_menu.setProperty("loc_key", "file_export")
        
        export_css_action = QAction(self.localization.tr("file_export_css", "Export CSS"), self)
        export_css_action.setProperty("loc_key", "file_export_css")
        export_css_action.triggered.connect(self.export_css)
        export_menu.addAction(export_css_action)
        
        export_scss_action = QAction(self.localization.tr("file_export_scss", "Export SCSS"), self)
        export_scss_action.setProperty("loc_key", "file_export_scss")
        export_scss_action.triggered.connect(lambda: self.export_format("scss"))
        export_menu.addAction(export_scss_action)
        
        export_less_action = QAction(self.localization.tr("file_export_less", "Export LESS"), self)
        export_less_action.setProperty("loc_key", "file_export_less")
        export_less_action.triggered.connect(lambda: self.export_format("less"))
        export_menu.addAction(export_less_action)
        
        export_sass_action = QAction(self.localization.tr("file_export_sass", "Export SASS"), self)
        export_sass_action.setProperty("loc_key", "file_export_sass")
        export_sass_action.triggered.connect(lambda: self.export_format("sass"))
        export_menu.addAction(export_sass_action)
        
        copy_css_action = QAction(self.localization.tr("file_copy_css", "Copy CSS"), self)
        copy_css_action.setProperty("loc_key", "file_copy_css")
        copy_css_action.triggered.connect(self.copy_css)
        file_menu.addAction(copy_css_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction(self.localization.tr("file_exit", "Exit"), self)
        exit_action.setProperty("loc_key", "file_exit")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu(self.localization.tr("menu_edit", "Edit"))
        edit_menu.setProperty("loc_key", "menu_edit")
        
        undo_action = QAction(self.localization.tr("edit_undo", "Undo"), self)
        undo_action.setProperty("loc_key", "edit_undo")
        undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        undo_action.triggered.connect(self.undo)
        edit_menu.addAction(undo_action)
        
        redo_action = QAction(self.localization.tr("edit_redo", "Redo"), self)
        redo_action.setProperty("loc_key", "edit_redo")
        redo_action.setShortcut(QKeySequence("Ctrl+Y"))
        redo_action.triggered.connect(self.redo)
        edit_menu.addAction(redo_action)
        
        edit_menu.addSeparator()
        
        duplicate_action = QAction(self.localization.tr("edit_duplicate", "Duplicate"), self)
        duplicate_action.setProperty("loc_key", "edit_duplicate")
        duplicate_action.setShortcut(QKeySequence("Ctrl+D"))
        duplicate_action.triggered.connect(self.duplicate_selected_element)
        edit_menu.addAction(duplicate_action)
        
        delete_action = QAction(self.localization.tr("edit_delete", "Delete"), self)
        delete_action.setProperty("loc_key", "edit_delete")
        delete_action.setShortcut(QKeySequence("Delete"))
        delete_action.triggered.connect(self.delete_selected_element)
        edit_menu.addAction(delete_action)
        
        # Elements menu
        elements_menu = menubar.addMenu(self.localization.tr("menu_elements", "Elements"))
        elements_menu.setProperty("loc_key", "menu_elements")
        
        add_div_action = QAction(self.localization.tr("elements_add_div", "Add Div"), self)
        add_div_action.setProperty("loc_key", "elements_add_div")
        add_div_action.triggered.connect(lambda: self.add_visual_element("div"))
        elements_menu.addAction(add_div_action)
        
        add_button_action = QAction(self.localization.tr("elements_add_button", "Add Button"), self)
        add_button_action.setProperty("loc_key", "elements_add_button")
        add_button_action.triggered.connect(lambda: self.add_visual_element("button"))
        elements_menu.addAction(add_button_action)
        
        add_section_action = QAction(self.localization.tr("elements_add_section", "Add Section"), self)
        add_section_action.setProperty("loc_key", "elements_add_section")
        add_section_action.triggered.connect(lambda: self.add_visual_element("section"))
        elements_menu.addAction(add_section_action)
        
        # Templates menu
        templates_menu = menubar.addMenu(self.localization.tr("menu_templates", "Templates"))
        templates_menu.setProperty("loc_key", "menu_templates")
        
        save_template_action = QAction(self.localization.tr("templates_save", "Save as Template"), self)
        save_template_action.setProperty("loc_key", "templates_save")
        save_template_action.triggered.connect(self.save_as_template)
        templates_menu.addAction(save_template_action)
        
        load_template_action = QAction(self.localization.tr("templates_load", "Load Template"), self)
        load_template_action.setProperty("loc_key", "templates_load")
        load_template_action.triggered.connect(self.load_template)
        templates_menu.addAction(load_template_action)
        
        templates_menu.addSeparator()
        
        button_template_action = QAction(self.localization.tr("templates_button", "Button"), self)
        button_template_action.setProperty("loc_key", "templates_button")
        button_template_action.triggered.connect(lambda: self.load_preset_template("button"))
        templates_menu.addAction(button_template_action)
        
        card_template_action = QAction(self.localization.tr("templates_card", "Card"), self)
        card_template_action.setProperty("loc_key", "templates_card")
        card_template_action.triggered.connect(lambda: self.load_preset_template("card"))
        templates_menu.addAction(card_template_action)
        
        form_template_action = QAction(self.localization.tr("templates_form", "Form"), self)
        form_template_action.setProperty("loc_key", "templates_form")
        form_template_action.triggered.connect(lambda: self.load_preset_template("form"))
        templates_menu.addAction(form_template_action)
        
        # View menu
        view_menu = menubar.addMenu(self.localization.tr("menu_view", "View"))
        view_menu.setProperty("loc_key", "menu_view")
        
        lang_menu = view_menu.addMenu(self.localization.tr("view_language", "Language"))
        lang_menu.setProperty("loc_key", "view_language")
        
        en_action = QAction(self.localization.tr("view_language_english", "English"), self)
        en_action.setProperty("loc_key", "view_language_english")
        en_action.triggered.connect(lambda: self.set_language("en"))
        lang_menu.addAction(en_action)
        
        ru_action = QAction(self.localization.tr("view_language_russian", "Russian"), self)
        ru_action.setProperty("loc_key", "view_language_russian")
        ru_action.triggered.connect(lambda: self.set_language("ru"))
        lang_menu.addAction(ru_action)
        
        view_menu.addSeparator()
        
        preview_bg_action = QAction(self.localization.tr("view_preview_bg", "Preview Background Color"), self)
        preview_bg_action.setProperty("loc_key", "view_preview_bg")
        preview_bg_action.triggered.connect(self.change_preview_bg_color)
        view_menu.addAction(preview_bg_action)
        
        snap_grid_action = QAction(self.localization.tr("view_snap_grid", "Snap to Grid"), self)
        snap_grid_action.setProperty("loc_key", "view_snap_grid")
        snap_grid_action.setCheckable(True)
        snap_grid_action.setChecked(self.visual_editor.snap_to_grid)
        snap_grid_action.triggered.connect(self.toggle_snap_to_grid)
        view_menu.addAction(snap_grid_action)
        
        show_grid_action = QAction(self.localization.tr("view_show_grid", "Show Grid"), self)
        show_grid_action.setProperty("loc_key", "view_show_grid")
        show_grid_action.setCheckable(True)
        show_grid_action.setChecked(self.visual_editor.show_grid)
        show_grid_action.triggered.connect(self.toggle_show_grid)
        view_menu.addAction(show_grid_action)
    
    def setup_toolbar(self):
        toolbar = QToolBar()
        self.addToolBar(toolbar)
        
        new_btn = QPushButton(self.localization.tr("file_new", "New"))
        new_btn.setProperty("loc_key", "file_new")
        new_btn.clicked.connect(self.new_project)
        toolbar.addWidget(new_btn)
        
        open_btn = QPushButton(self.localization.tr("file_open", "Open"))
        open_btn.setProperty("loc_key", "file_open")
        open_btn.clicked.connect(self.open_project)
        toolbar.addWidget(open_btn)
        
        save_btn = QPushButton(self.localization.tr("file_save", "Save"))
        save_btn.setProperty("loc_key", "file_save")
        save_btn.clicked.connect(self.save_project)
        toolbar.addWidget(save_btn)
        
        toolbar.addSeparator()
        
        export_btn = QPushButton(self.localization.tr("file_export_css", "Export CSS"))
        export_btn.setProperty("loc_key", "file_export_css")
        export_btn.clicked.connect(self.export_css)
        toolbar.addWidget(export_btn)
    
    def set_language(self, lang_code):
        self.current_language = lang_code
        self.localization.set_language(lang_code)
        self.update_ui_language()
    
    def update_ui_language(self):
        # Update window title
        self.setWindowTitle(self.localization.tr("app_name", "CSS Designer"))
        
        # Update status bar
        self.statusBar().showMessage(self.localization.tr("status_ready", "Ready"))
        
        # Update menu items
        menubar = self.menuBar()
        for action in menubar.actions():
            menu = action.menu()
            if menu:
                loc_key = menu.property("loc_key")
                if loc_key:
                    menu.setTitle(self.localization.tr(loc_key, ""))
                
                # Update menu actions
                for menu_action in menu.actions():
                    loc_key = menu_action.property("loc_key")
                    if loc_key:
                        menu_action.setText(self.localization.tr(loc_key, ""))
                    # Handle submenus
                    submenu = menu_action.menu()
                    if submenu:
                        submenu_loc_key = submenu.property("loc_key")
                        if submenu_loc_key:
                            submenu.setTitle(self.localization.tr(submenu_loc_key, ""))
                        for sub_action in submenu.actions():
                            sub_loc_key = sub_action.property("loc_key")
                            if sub_loc_key:
                                sub_action.setText(self.localization.tr(sub_loc_key, ""))
        
        # Update widgets
        for widget in self.findChildren(QWidget):
            loc_key = widget.property("loc_key")
            if loc_key:
                if isinstance(widget, QLabel):
                    widget.setText(self.localization.tr(loc_key, "") + (":" if "panel" in loc_key or "code" in loc_key else ""))
                elif isinstance(widget, QPushButton):
                    widget.setText(self.localization.tr(loc_key, ""))
                elif isinstance(widget, QTreeWidget):
                    widget.setHeaderLabel(self.localization.tr(loc_key, ""))
        
        # Update properties
        if hasattr(self, 'properties_panel'):
            self.properties_panel.update_language(self.localization)
    
    def add_visual_element(self, element_type="div"):
        element = self.visual_editor.add_element(element_type, 50, 50, 200, 100)
        self.update_code_editor()
        self.update_preview()
        self.save_state()
    
    def delete_element(self, element):
        """Delete selected element"""
        if element in self.visual_editor.elements:
            self.visual_editor.scene.removeItem(element)
            self.visual_editor.elements.remove(element)
            if self.visual_editor.selected_element == element:
                self.visual_editor.selected_element = None
            self.update_code_editor()
            self.update_preview()
            self.save_state()
            self.statusBar().showMessage(self.localization.tr("status_element_deleted", "Element deleted"))
    
    def duplicate_element(self, element):
        """Duplicate selected element"""
        if element in self.visual_editor.elements:
            pos = element.pos()
            rect = element.rect()
            new_element = self.visual_editor.add_element(
                element.element_name,
                pos.x() + 20, pos.y() + 20,
                rect.width(), rect.height()
            )
            # Copy styles
            new_element.styles = copy.deepcopy(element.styles)
            # Copy text
            if hasattr(element, 'text_content'):
                new_element.set_text(element.text_content)
            new_element.update_appearance()
            self.update_code_editor()
            self.update_preview()
            self.save_state()
            self.statusBar().showMessage(self.localization.tr("status_element_duplicated", "Element duplicated"))
    
    def copy_element(self, element):
        """Copy element to clipboard"""
        if element in self.visual_editor.elements:
            element_data = {
                "type": element.element_name,
                "styles": copy.deepcopy(element.styles),
                "pos": (float(element.pos().x()), float(element.pos().y())),
                "rect": (float(element.rect().x()), float(element.rect().y()), 
                        float(element.rect().width()), float(element.rect().height())),
                "text": element.text_content if hasattr(element, 'text_content') else ""
            }
            clipboard = QApplication.clipboard()
            clipboard.setText(json.dumps(element_data))
            self.statusBar().showMessage(self.localization.tr("status_element_copied", "Element copied"))
    
    def paste_element(self):
        """Paste element from clipboard"""
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        try:
            element_data = json.loads(text)
            if isinstance(element_data, dict) and "type" in element_data:
                pos = element_data.get("pos", (50, 50))
                rect_data = element_data.get("rect")
                if rect_data:
                    x, y, width, height = rect_data
                else:
                    styles = element_data.get("styles", {})
                    width = int(styles.get("width", "200px").replace("px", ""))
                    height = int(styles.get("height", "100px").replace("px", ""))
                    x, y = pos
                
                new_element = self.visual_editor.add_element(
                    element_data.get("type", "div"),
                    x + 20, y + 20,  # Offset for visibility
                    width, height
                )
                # Copy styles
                new_element.styles = copy.deepcopy(element_data.get("styles", {}))
                # Copy text
                if "text" in element_data:
                    new_element.set_text(element_data["text"])
                new_element.update_appearance()
                self.update_code_editor()
                self.update_preview()
                self.save_state()
                self.statusBar().showMessage(self.localization.tr("status_element_pasted", "Element pasted"))
        except (json.JSONDecodeError, ValueError):
            # Not a valid element data, ignore
            pass
    
    def delete_selected_element(self):
        """Delete currently selected element"""
        if self.visual_editor.selected_element:
            self.delete_element(self.visual_editor.selected_element)
    
    def duplicate_selected_element(self):
        """Duplicate currently selected element"""
        if self.visual_editor.selected_element:
            self.duplicate_element(self.visual_editor.selected_element)
    
    def on_element_selected(self, element):
        self.properties_panel.set_element(element)
        if not self.code_update_blocked:
            self.update_code_editor()
    
    def on_element_visual_changed(self):
        # Debounce preview updates to improve performance
        if not hasattr(self, 'preview_update_timer'):
            self.preview_update_timer = QTimer()
            self.preview_update_timer.setSingleShot(True)
            self.preview_update_timer.timeout.connect(self.update_preview)
        
        # Update preview with debounce (300ms delay)
        self.preview_update_timer.stop()
        self.preview_update_timer.start(300)
        
        if not self.code_update_blocked:
            self.update_timer.start(200)  # Delay to prevent rapid updates
    
    def on_style_changed(self, property_name, value):
        if not self.code_update_blocked:
            self.update_code_editor()
        self.update_preview()
        self.save_state()
    
    def on_text_changed(self, text):
        if not self.code_update_blocked:
            self.update_code_editor()
        self.update_preview()
        self.save_state()
    
    def on_code_changed(self):
        if self.code_update_blocked:
            return
        
        css = self.code_editor.toPlainText()
        self.parse_css_and_apply(css)
        self.update_preview()
        # Save state after a delay to avoid too frequent saves
        if hasattr(self, 'save_timer'):
            self.save_timer.stop()
        else:
            self.save_timer = QTimer()
            self.save_timer.setSingleShot(True)
            self.save_timer.timeout.connect(self.save_state)
        self.save_timer.start(500)
    
    def parse_css_and_apply(self, css_text):
        # Parse CSS rules and apply to elements
        if not css_text.strip():
            return
        
        # Block updates to prevent infinite loop
        self.code_update_blocked = True
        
        # Find all CSS rules - support both old format (.div-element) and new format (.div-element-0)
        pattern = r'\.(\w+)-element(?:-(\d+))?\s*\{([^}]+)\}'
        matches = list(re.finditer(pattern, css_text, re.MULTILINE | re.DOTALL))
        
        elements_updated = False
        processed_indices = set()
        
        for match in matches:
            class_name = match.group(1)
            element_index_str = match.group(2)
            properties_text = match.group(3)
            
            # Parse properties
            properties = {}
            # Remove comments first
            properties_text = re.sub(r'/\*.*?\*/', '', properties_text, flags=re.DOTALL)
            # Split by semicolon and parse
            prop_lines = properties_text.split(';')
            for prop_line in prop_lines:
                prop_line = prop_line.strip()
                if ':' in prop_line:
                    parts = prop_line.split(':', 1)
                    if len(parts) == 2:
                        prop_name = parts[0].strip()
                        prop_value = parts[1].strip()
                        if prop_name and prop_value:
                            properties[prop_name] = prop_value
            
            # Extract position and size from properties
            left = int(properties.get('left', '0px').replace('px', ''))
            top = int(properties.get('top', '0px').replace('px', ''))
            width = int(properties.get('width', '200px').replace('px', ''))
            height = int(properties.get('height', '100px').replace('px', ''))
            
            element = None
            element_index = None
            
            if element_index_str is not None:
                # New format with index
                element_index = int(element_index_str)
                if element_index < len(self.visual_editor.elements):
                    elem = self.visual_editor.elements[element_index]
                    if elem.element_name.lower() == class_name:
                        element = elem
                        processed_indices.add(element_index)
            else:
                # Old format without index - find first matching element that hasn't been processed
                for i, elem in enumerate(self.visual_editor.elements):
                    if elem.element_name.lower() == class_name and i not in processed_indices:
                        element = elem
                        element_index = i
                        processed_indices.add(i)
                        break
            
            if element:
                # Update existing element
                for prop_name, prop_value in properties.items():
                    old_value = element.styles.get(prop_name)
                    if old_value != prop_value:
                        element.set_style(prop_name, prop_value)
                        elements_updated = True
                
                # Update position if changed
                if 'left' in properties or 'top' in properties:
                    element.setPos(left, top)
                
                # Update properties panel if this element is selected
                if self.visual_editor.selected_element == element:
                    self.properties_panel.set_element(element)
            else:
                # Create new element if not found
                new_element = self.visual_editor.add_element(
                    class_name,
                    left, top,
                    width, height
                )
                # Apply all properties
                for prop_name, prop_value in properties.items():
                    if prop_name not in ['left', 'top', 'width', 'height']:
                        new_element.set_style(prop_name, prop_value)
                elements_updated = True
        
        # Refresh visual editor if elements were updated
        if elements_updated:
            self.visual_editor.scene.update()
            self.save_state()
            self.update_code_editor()
        
        self.code_update_blocked = False
    
    def update_code_editor(self):
        if self.code_update_blocked:
            return
        
        self.code_update_blocked = True
        cursor_pos = self.code_editor.textCursor().position()
        css = self.generate_css()
        self.code_editor.setPlainText(css)
        
        # Restore cursor position if possible
        if cursor_pos < len(css):
            cursor = self.code_editor.textCursor()
            cursor.setPosition(cursor_pos)
            self.code_editor.setTextCursor(cursor)
        
        self.code_update_blocked = False
    
    def generate_css(self):
        css = self.visual_editor.get_all_css()
        return css
    
    def update_preview(self):
        css = self.generate_css()
        
        if self.html_content:
            html = self.html_content
            if "<style>" in html:
                html = re.sub(r'<style>.*?</style>', f'<style>\n{css}\n</style>', html, flags=re.DOTALL)
            elif "<head>" in html:
                html = html.replace("</head>", f"<style>\n{css}\n</style>\n</head>")
            else:
                html = f"<head><style>\n{css}\n</style></head>\n{html}"
        else:
            preview_html = self.generate_preview_html()
            html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * {{
            box-sizing: border-box;
        }}
        body {{
            margin: 0;
            padding: 20px;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            position: relative;
            min-height: 100vh;
            background-color: {self.preview_bg_color};
            color: #ffffff;
        }}
        .card-element .card-header {{
            padding: 10px 15px;
            background-color: #f8f9fa;
            border-bottom: 1px solid #dee2e6;
            font-weight: bold;
        }}
        .card-element .card-body {{
            padding: 15px;
        }}
        .card-element .card-footer {{
            padding: 10px 15px;
            background-color: #f8f9fa;
            border-top: 1px solid #dee2e6;
            font-size: 0.9em;
            color: #6c757d;
        }}
    </style>
</head>
<body>
    {preview_html}
</body>
</html>"""
        
        try:
            if HAS_WEBENGINE:
                self.preview_web.setHtml(html)
            else:
                self.preview_web.setHtml(html)
        except Exception as e:
            print(f"Error updating preview: {e}")
    
    def change_preview_bg_color(self):
        current_color = QColor(self.preview_bg_color)
        color = QColorDialog.getColor(current_color, self, self.localization.tr("dialog_preview_bg", "Choose Preview Background Color"))
        if color.isValid():
            self.preview_bg_color = color.name()
            self.update_preview()
            self.statusBar().showMessage(self.localization.tr("status_bg_changed", "Background color changed"))
    
    def toggle_snap_to_grid(self, checked):
        self.visual_editor.snap_to_grid = checked
        self.statusBar().showMessage(
            self.localization.tr("status_snap_enabled", "Snap to grid enabled") if checked 
            else self.localization.tr("status_snap_disabled", "Snap to grid disabled")
        )
    
    def toggle_show_grid(self, checked):
        self.visual_editor.show_grid = checked
        self.visual_editor.scene.update()
        self.statusBar().showMessage(
            self.localization.tr("status_grid_shown", "Grid shown") if checked 
            else self.localization.tr("status_grid_hidden", "Grid hidden")
        )
    
    def generate_preview_html(self):
        html = ""
        for i, element in enumerate(self.visual_editor.elements):
            # Get current position from element
            pos = element.pos()
            current_left = f'{int(pos.x())}px'
            current_top = f'{int(pos.y())}px'
            
            # Build styles with current position
            styles = element.styles.copy()
            styles['left'] = current_left
            styles['top'] = current_top
            # Ensure position is absolute for proper positioning
            if 'position' not in styles or styles.get('position') == 'static':
                styles['position'] = 'absolute'
            
            # Ensure display is set for block elements
            element_type = element.element_name.lower()
            if element_type in ['div', 'section', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'card']:
                if 'display' not in styles:
                    styles['display'] = 'block'

            # Use !important for critical positioning and sizing properties to ensure they override any CSS
            styles_list = []
            critical_props = ['position', 'left', 'top', 'width', 'height']
            for k, v in styles.items():
                if k in critical_props:
                    styles_list.append(f"{k}: {v} !important")
                else:
                    styles_list.append(f"{k}: {v}")
            styles_str = "; ".join(styles_list)
            text = element.text_content if hasattr(element, 'text_content') and element.text_content else ""
            
            # Use appropriate HTML tag based on element type
            if element_type == "button":
                html += f'<button style="{styles_str}">{text or "Button"}</button>\n'
            elif element_type == "input":
                input_type = element.styles.get('type', 'text')
                html += f'<input type="{input_type}" style="{styles_str}" placeholder="{text or ""}">\n'
            elif element_type == "card":
                # Card structure with header, body, footer
                card_content = text or "Card Content"
                html += f'''<div style="{styles_str}">
                    <div style="padding: 10px 15px; background-color: #f8f9fa; border-bottom: 1px solid #dee2e6; font-weight: bold;">Card Header</div>
                    <div style="padding: 15px;">{card_content}</div>
                    <div style="padding: 10px 15px; background-color: #f8f9fa; border-top: 1px solid #dee2e6; font-size: 0.9em; color: #6c757d;">Card Footer</div>
                </div>\n'''
            elif element_type == "h1" or element_type == "h2" or element_type == "h3" or element_type == "h4" or element_type == "h5" or element_type == "h6":
                html += f'<{element_type} style="{styles_str}">{text or element_type.upper()}</{element_type}>\n'
            elif element_type == "p":
                html += f'<p style="{styles_str}">{text or "Paragraph text"}</p>\n'
            elif element_type == "span":
                html += f'<span style="{styles_str}">{text or "Span text"}</span>\n'
            elif element_type == "img":
                src = text or "https://via.placeholder.com/200x100"
                html += f'<img src="{src}" alt="Image" style="{styles_str}">\n'
            elif element_type == "a":
                html += f'<a href="#" style="{styles_str}">{text or "Link"}</a>\n'
            else:
                # Default to div
                html += f'<div style="{styles_str}">{text or f"Element {i+1}"}</div>\n'
        return html
    
    
    def add_component(self):
        name, ok = QInputDialog.getText(self, self.localization.tr("dialog_new_component", "New Component"), 
                                       self.localization.tr("dialog_component_name", "Component name:") + " ")
        if ok and name:
            item = QTreeWidgetItem(self.components_tree)
            item.setText(0, name)
            self.components_tree.addTopLevelItem(item)
            self.save_state()
    
    def remove_component(self):
        current = self.components_tree.currentItem()
        if current:
            self.components_tree.takeTopLevelItem(self.components_tree.indexOfTopLevelItem(current))
            self.save_state()
    
    def on_component_selected(self, item, column):
        if item:
            component_name = item.text(0)
            self.statusBar().showMessage(f"{self.localization.tr('status_component_selected', 'Component selected')}: {component_name}")
    
    def add_media_query(self):
        name, ok = QInputDialog.getText(self, self.localization.tr("dialog_new_media", "New Media Query"), 
                                       self.localization.tr("dialog_media_name", "Name (e.g., mobile, tablet):") + " ")
        if ok and name:
            self.media_queries_list.addItem(name)
            self.save_state()
    
    def remove_media_query(self):
        current = self.media_queries_list.currentItem()
        if current:
            row = self.media_queries_list.row(current)
            self.media_queries_list.takeItem(row)
            self.save_state()
        else:
            QMessageBox.information(self, self.localization.tr("dialog_info", "Information"), 
                                   self.localization.tr("dialog_select_media", "Please select a media query to remove"))
    
    def save_state(self):
        current_state = {
            "elements": [{
                "type": e.element_name, 
                "styles": copy.deepcopy(e.styles), 
                "pos": (float(e.pos().x()), float(e.pos().y())),
                "rect": (float(e.rect().x()), float(e.rect().y()), float(e.rect().width()), float(e.rect().height())),
                "text": e.text_content if hasattr(e, 'text_content') else ""
            } for e in self.visual_editor.elements]
        }
        
        # Only save if state actually changed
        if self.history_index >= 0 and len(self.project_data["history"]) > 0:
            last_entry = self.project_data["history"][self.history_index]
            last_state = self._get_full_state(last_entry)
            if last_state == current_state:
                return  # No changes, skip saving
        
        # Store only changes if possible
        if self.history_index >= 0 and len(self.project_data["history"]) > 0:
            last_entry = self.project_data["history"][self.history_index]
            last_state = self._get_full_state(last_entry)
            diff = self._calculate_state_diff(last_state, current_state)
            if diff and len(diff.get("changes", [])) < len(current_state.get("elements", [])):
                # Store diff if it's smaller than full state
                self.project_data["history"] = self.project_data["history"][:self.history_index + 1]
                self.project_data["history"].append({"type": "diff", "data": diff, "base_index": self.history_index})
                self.history_index = len(self.project_data["history"]) - 1
            else:
                # Store full state
                self.project_data["history"] = self.project_data["history"][:self.history_index + 1]
                self.project_data["history"].append({"type": "full", "data": current_state})
                self.history_index = len(self.project_data["history"]) - 1
        else:
            # First state, store full
            self.project_data["history"] = self.project_data["history"][:self.history_index + 1]
            self.project_data["history"].append({"type": "full", "data": current_state})
            self.history_index = len(self.project_data["history"]) - 1
        
        # Limit history size to prevent memory issues
        max_history = 100
        if len(self.project_data["history"]) > max_history:
            # Keep only recent history
            self.project_data["history"] = self.project_data["history"][-max_history:]
            self.history_index = len(self.project_data["history"]) - 1
    
    def _calculate_state_diff(self, old_state, new_state):
        """Calculate difference between two states for differential storage"""
        old_elements = {i: elem for i, elem in enumerate(old_state.get("elements", []))}
        new_elements = {i: elem for i, elem in enumerate(new_state.get("elements", []))}
        
        changes = []
        # Find modified elements
        for i in range(max(len(old_elements), len(new_elements))):
            if i not in old_elements:
                changes.append({"action": "add", "index": i, "element": new_elements[i]})
            elif i not in new_elements:
                changes.append({"action": "remove", "index": i})
            elif old_elements[i] != new_elements[i]:
                changes.append({"action": "modify", "index": i, "element": new_elements[i]})
        
        return {"changes": changes} if changes else None
    
    def _apply_state_diff(self, base_state, diff):
        """Apply diff to base state to reconstruct full state"""
        state = copy.deepcopy(base_state)
        elements = state.get("elements", [])
        
        for change in diff.get("changes", []):
            action = change.get("action")
            index = change.get("index")
            
            if action == "add":
                elements.insert(index, change.get("element"))
            elif action == "remove":
                if index < len(elements):
                    elements.pop(index)
            elif action == "modify":
                if index < len(elements):
                    elements[index] = change.get("element")
        
        state["elements"] = elements
        return state
    
    def _get_full_state(self, history_entry):
        """Get full state from history entry (handles both full and diff entries)"""
        if history_entry.get("type") == "full":
            return history_entry.get("data")
        elif history_entry.get("type") == "diff":
            base_index = history_entry.get("base_index")
            if base_index >= 0 and base_index < len(self.project_data["history"]):
                base_state = self._get_full_state(self.project_data["history"][base_index])
                return self._apply_state_diff(base_state, history_entry.get("data"))
        return {}
    
    def undo(self):
        if self.history_index > 0:
            self.history_index -= 1
            history_entry = self.project_data["history"][self.history_index]
            # Handle both old format (direct state) and new format (with type)
            if isinstance(history_entry, dict) and "type" in history_entry:
                # New format
                full_state = self._get_full_state(history_entry)
                self.load_state(full_state)
            else:
                # Old format - direct state
                self.load_state(history_entry)
            self.statusBar().showMessage(self.localization.tr("status_undo", "Undone"))
    
    def redo(self):
        if self.history_index < len(self.project_data["history"]) - 1:
            self.history_index += 1
            history_entry = self.project_data["history"][self.history_index]
            # Handle both old format (direct state) and new format (with type)
            if isinstance(history_entry, dict) and "type" in history_entry:
                # New format
                full_state = self._get_full_state(history_entry)
                self.load_state(full_state)
            else:
                # Old format - direct state
                self.load_state(history_entry)
            self.statusBar().showMessage(self.localization.tr("status_redo", "Redone"))
    
    def load_state(self, state):
        self.visual_editor.scene.clear()
        self.visual_editor.elements = []
        self.visual_editor.selected_element = None
        
        if "elements" in state:
            for elem_data in state["elements"]:
                element_type = elem_data.get("type", "div")
                styles = elem_data.get("styles", {})
                pos = elem_data.get("pos", (50, 50))
                rect_data = elem_data.get("rect")
                text = elem_data.get("text", "")
                
                if rect_data:
                    x, y, width, height = rect_data
                else:
                    width = int(styles.get("width", "200px").replace("px", ""))
                    height = int(styles.get("height", "100px").replace("px", ""))
                    x, y = pos
                
                rect = QRectF(x, y, width, height)
                element = DraggableRectItem(rect, element_type)
                self.visual_editor.scene.addItem(element)
                self.visual_editor.elements.append(element)
                
                for prop, value in styles.items():
                    element.set_style(prop, value)
                
                if text:
                    element.set_text(text)
        
        self.update_code_editor()
        self.update_preview()
    
    def new_project(self):
        reply = QMessageBox.question(self, self.localization.tr("file_new", "New Project"), 
                                    self.localization.tr("dialog_new_project", "Create new project? Unsaved changes will be lost."),
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            self.project_data = {
                "name": self.localization.tr("file_new", "New Project"),
                "components": [],
                "history": [],
                "templates": [],
                "html_content": ""
            }
            self.html_content = ""
            self.visual_editor.scene.clear()
            self.visual_editor.elements = []
            self.components_tree.clear()
            self.media_queries_list.clear()
            self.update_code_editor()
            self.update_preview()
            self.statusBar().showMessage(self.localization.tr("status_new_project", "New project created"))
    
    def open_project(self):
        filename, _ = QFileDialog.getOpenFileName(self, self.localization.tr("file_open", "Open"), "", "JSON Files (*.json)")
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    self.project_data = json.load(f)
                
                self.visual_editor.scene.clear()
                self.visual_editor.elements = []
                
                if "history" in self.project_data and len(self.project_data["history"]) > 0:
                    # Handle both old format (direct state) and new format (with type)
                    last_entry = self.project_data["history"][-1]
                    if isinstance(last_entry, dict) and "type" in last_entry:
                        # New format
                        full_state = self._get_full_state(last_entry)
                        self.load_state(full_state)
                    else:
                        # Old format - direct state
                        self.load_state(last_entry)
                    self.history_index = len(self.project_data["history"]) - 1
                
                self.html_content = self.project_data.get("html_content", "")
                
                self.update_preview()
                self.statusBar().showMessage(f"{self.localization.tr('status_project_loaded', 'Project loaded')}: {filename}")
            except Exception as e:
                QMessageBox.critical(self, self.localization.tr("dialog_error", "Error"), 
                                   f"{self.localization.tr('dialog_failed_load', 'Failed to load project')}:\n{str(e)}")
    
    def save_project(self):
        filename, _ = QFileDialog.getSaveFileName(self, self.localization.tr("file_save", "Save"), "", "JSON Files (*.json)")
        if filename:
            try:
                self.save_state()
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(self.project_data, f, ensure_ascii=False, indent=2)
                
                self.statusBar().showMessage(f"{self.localization.tr('status_project_saved', 'Project saved')}: {filename}")
            except Exception as e:
                QMessageBox.critical(self, self.localization.tr("dialog_error", "Error"), 
                                   f"{self.localization.tr('dialog_failed_save', 'Failed to save project')}:\n{str(e)}")
    
    def export_css(self):
        filename, _ = QFileDialog.getSaveFileName(self, self.localization.tr("file_export_css", "Export CSS"), "", "CSS Files (*.css)")
        if filename:
            try:
                css = self.generate_css()
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(css)
                self.statusBar().showMessage(f"{self.localization.tr('status_css_exported', 'CSS exported')}: {filename}")
            except Exception as e:
                QMessageBox.critical(self, self.localization.tr("dialog_error", "Error"), 
                                   f"{self.localization.tr('dialog_failed_export', 'Failed to export CSS')}:\n{str(e)}")
    
    def export_format(self, format_type):
        """Export CSS in specific format"""
        extensions = {
            "scss": "SCSS Files (*.scss)",
            "less": "LESS Files (*.less)",
            "sass": "SASS Files (*.sass)"
        }
        filename, _ = QFileDialog.getSaveFileName(self, 
                                                 self.localization.tr(f"file_export_{format_type}", f"Export {format_type.upper()}"), 
                                                 "", extensions.get(format_type, "CSS Files (*.css)"))
        if filename:
            try:
                css = self.generate_css()
                if format_type == 'scss':
                    css = self._convert_to_scss(css)
                elif format_type == 'less':
                    css = self._convert_to_less(css)
                elif format_type == 'sass':
                    css = self._convert_to_sass(css)
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(css)
                self.statusBar().showMessage(f"{self.localization.tr('status_css_exported', 'CSS exported')}: {filename}")
            except Exception as e:
                QMessageBox.critical(self, self.localization.tr("dialog_error", "Error"), 
                                   f"{self.localization.tr('dialog_failed_export', 'Failed to export CSS')}:\n{str(e)}")
    
    def _convert_to_scss(self, css):
        """Convert CSS to SCSS format with nesting"""
        lines = css.split('\n')
        scss = []
        indent_level = 0
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                scss.append('')
                continue
            
            # Check if it's a selector
            if stripped.endswith('{'):
                selector = stripped[:-1].strip()
                scss.append(' ' * indent_level + selector + ' {')
                indent_level += 2
            elif stripped == '}':
                indent_level = max(0, indent_level - 2)
                scss.append(' ' * indent_level + '}')
            else:
                # Property
                scss.append(' ' * indent_level + stripped)
        
        return '\n'.join(scss)
    
    def _convert_to_less(self, css):
        """Convert CSS to LESS format (similar to SCSS)"""
        return self._convert_to_scss(css)  # LESS syntax is similar to SCSS
    
    def _convert_to_sass(self, css):
        """Convert CSS to SASS format (indented syntax)"""
        lines = css.split('\n')
        sass = []
        indent_level = 0
        
        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            
            # Check if it's a selector
            if stripped.endswith('{'):
                selector = stripped[:-1].strip()
                sass.append(' ' * indent_level + selector)
                indent_level += 2
            elif stripped == '}':
                indent_level = max(0, indent_level - 2)
            else:
                # Property - SASS uses : instead of :
                if ':' in stripped:
                    prop, value = stripped.split(':', 1)
                    sass.append(' ' * indent_level + prop.strip() + ': ' + value.strip().rstrip(';'))
        
        return '\n'.join(sass)
    
    def copy_css(self):
        css = self.generate_css()
        clipboard = QApplication.clipboard()
        clipboard.setText(css)
        self.statusBar().showMessage(self.localization.tr("status_css_copied", "CSS copied to clipboard"))
    
    def open_html(self):
        filename, _ = QFileDialog.getOpenFileName(self, self.localization.tr("file_open_html", "Open HTML"), "", "HTML Files (*.html *.htm)")
        if filename:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    self.html_content = f.read()
                
                self.project_data["html_content"] = self.html_content
                self.update_preview()
                self.statusBar().showMessage(f"{self.localization.tr('file_open_html', 'HTML loaded')}: {filename}")
            except Exception as e:
                QMessageBox.critical(self, self.localization.tr("dialog_error", "Error"), 
                                   f"{self.localization.tr('dialog_failed_load_html', 'Failed to load HTML')}:\n{str(e)}")
    
    def edit_html(self):
        from PyQt6.QtWidgets import QDialog, QVBoxLayout, QTextEdit, QPushButton, QHBoxLayout, QLabel
        
        dialog = QDialog(self)
        dialog.setWindowTitle(self.localization.tr("file_edit_html", "Edit HTML"))
        dialog.setGeometry(100, 100, 900, 700)
        
        layout = QVBoxLayout()
        dialog.setLayout(layout)
        
        # Validation label
        validation_label = QLabel("")
        validation_label.setStyleSheet("color: red; padding: 5px;")
        layout.addWidget(validation_label)
        
        html_editor = QTextEdit()
        html_editor.setPlainText(self.html_content if self.html_content else "")
        html_editor.setFont(QFont("Courier", 10))
        
        # Add HTML syntax highlighting
        highlighter = HTMLHighlighter(html_editor.document())
        
        # Auto-completion for HTML tags
        html_tags = ['div', 'span', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'a', 'img', 'button', 'input', 'form', 'table', 'tr', 'td', 'ul', 'ol', 'li', 'section', 'article', 'header', 'footer', 'nav', 'aside', 'main']
        
        def on_text_changed():
            text = html_editor.toPlainText()
            errors = validate_html(text)
            if errors:
                validation_label.setText(self.localization.tr("html_validation_errors", "Validation errors") + ": " + "; ".join(errors[:3]))
                validation_label.setStyleSheet("color: red; padding: 5px; background-color: #ffeeee;")
            else:
                validation_label.setText(self.localization.tr("html_validation_ok", "HTML is valid"))
                validation_label.setStyleSheet("color: green; padding: 5px; background-color: #eeffee;")
        
        html_editor.textChanged.connect(on_text_changed)
        on_text_changed()  # Initial validation
        
        layout.addWidget(html_editor)
        
        button_layout = QHBoxLayout()
        save_btn = QPushButton(self.localization.tr("file_save", "Save"))
        save_btn.clicked.connect(lambda: self.save_html_from_editor(html_editor.toPlainText(), dialog))
        cancel_btn = QPushButton(self.localization.tr("file_cancel", "Cancel"))
        cancel_btn.clicked.connect(dialog.reject)
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        dialog.exec()
    
    def save_html_from_editor(self, html_text, dialog):
        self.html_content = html_text
        self.project_data["html_content"] = self.html_content
        self.update_preview()
        dialog.accept()
        self.statusBar().showMessage(self.localization.tr("status_html_saved", "HTML saved"))
    
    def save_as_template(self):
        if not self.visual_editor.selected_element:
            QMessageBox.warning(self, self.localization.tr("dialog_warning", "Warning"), 
                              self.localization.tr("dialog_select_element", "Select an element to save as template"))
            return
        
        name, ok = QInputDialog.getText(self, self.localization.tr("dialog_save_template", "Save Template"), 
                                       self.localization.tr("dialog_template_name", "Template name:") + " ")
        if ok and name:
            element = self.visual_editor.selected_element
            template = {
                "name": name,
                "element_type": element.element_name,
                "styles": copy.deepcopy(element.styles),
                "width": element.rect().width(),
                "height": element.rect().height(),
                "text": element.text_content if hasattr(element, 'text_content') else ""
            }
            
            if "templates" not in self.project_data:
                self.project_data["templates"] = []
            
            self.project_data["templates"].append(template)
            self.statusBar().showMessage(f"{self.localization.tr('status_template_saved', 'Template saved')}: {name}")
    
    def load_template(self):
        if "templates" not in self.project_data or len(self.project_data["templates"]) == 0:
            QMessageBox.information(self, self.localization.tr("dialog_info", "Information"), 
                                   self.localization.tr("dialog_no_templates", "No saved templates"))
            return
        
        templates_list = [t["name"] for t in self.project_data["templates"]]
        template_name, ok = QInputDialog.getItem(self, self.localization.tr("dialog_load_template", "Load Template"), 
                                                self.localization.tr("dialog_select_template", "Select template:") + " ", 
                                                templates_list, 0, False)
        
        if ok:
            template = next((t for t in self.project_data["templates"] if t["name"] == template_name), None)
            if template:
                self.apply_template(template)
                self.statusBar().showMessage(f"{self.localization.tr('status_template_loaded', 'Template loaded')}: {template_name}")
    
    def load_preset_template(self, template_type):
        templates = {
            "button": {
                "name": "Button",
                "element_type": "button",
                "styles": {
                    "background-color": "#007bff",
                    "color": "#ffffff",
                    "padding": "10px 20px",
                    "border": "none",
                    "border-radius": "4px",
                    "font-size": "16px",
                    "font-weight": "bold",
                    "cursor": "pointer",
                    "width": "120px",
                    "height": "40px"
                },
                "width": 120,
                "height": 40,
                "text": "Button"
            },
            "card": {
                "name": "Card",
                "element_type": "div",
                "styles": {
                    "background-color": "#ffffff",
                    "border": "1px solid #e0e0e0",
                    "border-radius": "8px",
                    "padding": "20px",
                    "box-shadow": "0 2px 4px rgba(0,0,0,0.1)",
                    "width": "300px",
                    "height": "200px"
                },
                "width": 300,
                "height": 200,
                "text": "Card Content"
            },
            "form": {
                "name": "Form",
                "element_type": "form",
                "styles": {
                    "background-color": "#f8f9fa",
                    "border": "1px solid #dee2e6",
                    "border-radius": "4px",
                    "padding": "20px",
                    "width": "400px",
                    "height": "300px"
                },
                "width": 400,
                "height": 300,
                "text": "Form"
            }
        }
        
        if template_type in templates:
            self.apply_template(templates[template_type])
            self.statusBar().showMessage(f"{self.localization.tr('status_template_loaded', 'Template loaded')}: {templates[template_type]['name']}")
    
    def apply_template(self, template):
        element = self.visual_editor.add_element(
            template["element_type"],
            50, 50,
            template.get("width", 200),
            template.get("height", 100)
        )
        
        for prop, value in template.get("styles", {}).items():
            element.set_style(prop, value)
        
        if "text" in template:
            element.set_text(template["text"])
        
        self.save_state()
        self.update_code_editor()
        self.update_preview()


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    window = CSSDesignerApp()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()