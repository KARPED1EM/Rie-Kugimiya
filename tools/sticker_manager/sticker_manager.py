#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
表情包管理工具
独立的桌面应用程序，用于管理 data/stickers 目录的表情包
"""

import sys
import shutil
import urllib.request
import time
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QGridLayout, QScrollArea,
    QMessageBox, QInputDialog, QFileDialog, QDialog, QDialogButtonBox,
    QLineEdit, QToolBar, QSplitter, QFrame, QMenu, QStatusBar
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QMimeData, QPoint, QSize, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QPixmap, QImage, QDragEnterEvent, QDropEvent, QAction, QPalette, QColor

# 导入类别映射
from sticker_categories import CATEGORY_MAP, CHINESE_TO_ROMAJI


class Toast(QLabel):
    """Toast通知组件"""
    
    def __init__(self, message: str, parent=None, success=True):
        super().__init__(message, parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 样式
        bg_color = "#4CAF50" if success else "#f44336"
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {bg_color};
                color: white;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 13px;
                font-weight: 500;
            }}
        """)
        
        # 设置固定大小和位置
        self.setMinimumWidth(200)
        self.adjustSize()
        
        # 淡入淡出动画
        self.setWindowOpacity(0)
        
    def show_toast(self):
        """显示Toast"""
        # 淡入
        self.show()
        self.fade_in()
        
        # 3秒后淡出
        QTimer.singleShot(3000, self.fade_out)
        
    def fade_in(self):
        """淡入动画"""
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(200)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.animation.start()
        
    def fade_out(self):
        """淡出动画"""
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(200)
        self.animation.setStartValue(1)
        self.animation.setEndValue(0)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.animation.finished.connect(self.hide)
        self.animation.start()


class StickerWidget(QFrame):
    """单个表情包的显示组件"""
    delete_clicked = pyqtSignal(str)  # 发送文件路径
    
    def __init__(self, image_path: Path, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        
        # 图片显示
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedSize(150, 150)
        self.image_label.setStyleSheet("""
            QLabel {
                border: 1px solid #e0e0e0;
                background: white;
                border-radius: 6px;
            }
        """)
        
        # 加载图片
        pixmap = QPixmap(str(self.image_path))
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(
                140, 140,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
        
        # 文件名 - 只显示编号
        name_label = QLabel(self.image_path.stem)  # 不显示扩展名
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        name_label.setMaximumWidth(150)
        name_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #666;
                font-weight: 500;
            }
        """)
        
        # 删除按钮
        delete_btn = QPushButton("🗑️ 删除")
        delete_btn.setMaximumWidth(150)
        delete_btn.clicked.connect(lambda: self.delete_clicked.emit(str(self.image_path)))
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffebee;
                color: #c62828;
                border: 1px solid #ef9a9a;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #ffcdd2;
                border-color: #e57373;
            }
            QPushButton:pressed {
                background-color: #ef9a9a;
            }
        """)
        
        layout.addWidget(self.image_label)
        layout.addWidget(name_label)
        layout.addWidget(delete_btn)
        
        self.setLayout(layout)
        self.setStyleSheet("""
            QFrame {
                background: white;
                border-radius: 8px;
                border: 2px solid #f5f5f5;
            }
            QFrame:hover {
                border: 2px solid #2196F3;
                box-shadow: 0 2px 8px rgba(33, 150, 243, 0.2);
            }
        """)


class GalleryArea(QWidget):
    """支持拖放的图库区域"""
    files_dropped = pyqtSignal(list)  # 发送文件路径列表
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setup_ui()
        
    def setup_ui(self):
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 2px dashed #e0e0e0;
                background: #fafafa;
                border-radius: 8px;
            }
        """)
        
        self.sticker_container = QWidget()
        self.sticker_layout = QGridLayout(self.sticker_container)
        self.sticker_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.sticker_layout.setSpacing(16)
        self.sticker_container.setStyleSheet("background: transparent;")
        
        self.scroll_area.setWidget(self.sticker_container)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.scroll_area)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.acceptProposedAction()
            # 高亮边框
            self.scroll_area.setStyleSheet("""
                QScrollArea {
                    border: 2px dashed #2196F3;
                    background: #e3f2fd;
                    border-radius: 8px;
                }
            """)
            
    def dragLeaveEvent(self, event):
        # 恢复边框
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 2px dashed #e0e0e0;
                background: #fafafa;
                border-radius: 8px;
            }
        """)
            
    def dropEvent(self, event: QDropEvent):
        # 恢复边框
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: 2px dashed #e0e0e0;
                background: #fafafa;
                border-radius: 8px;
            }
        """)
        
        mime_data = event.mimeData()
        files = []
        
        if mime_data.hasUrls():
            for url in mime_data.urls():
                if url.isLocalFile():
                    files.append(url.toLocalFile())
                else:
                    # 处理网络URL
                    files.append(url.toString())
        elif mime_data.hasImage():
            # 直接拖放的图片数据
            image = mime_data.imageData()
            if image:
                files.append(image)
                
        if files:
            self.files_dropped.emit(files)


class StickerManagerWindow(QMainWindow):
    """表情包管理主窗口"""
    
    def __init__(self):
        super().__init__()
        # 使用相对路径，从 tools/sticker_manager 到项目根目录
        self.sticker_base = Path(__file__).parent.parent.parent / "data" / "stickers"
        self.current_collection = None
        self.current_category = None
        self.category_buttons = []  # 保存所有类别按钮的引用
        self.setup_ui()
        self.apply_light_theme()
        self.load_collections()
        
    def setup_ui(self):
        self.setWindowTitle("表情包管理工具")
        self.setMinimumSize(1100, 750)
        
        # 主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 顶部工具栏
        toolbar = self.create_toolbar()
        main_layout.addWidget(toolbar)
        
        # 分割器：左侧类别列表，右侧表情包展示
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧类别选择
        category_widget = self.create_category_widget()
        splitter.addWidget(category_widget)
        
        # 右侧内容区域 - 直接是图库区域（移除了独立的拖放区）
        self.gallery_area = GalleryArea()
        self.gallery_area.files_dropped.connect(self.handle_dropped_files)
        splitter.addWidget(self.gallery_area)
        
        splitter.setStretchFactor(0, 0)  # 类别列表固定宽度
        splitter.setStretchFactor(1, 1)  # 图库区域可扩展
        splitter.setSizes([220, 880])  # 初始宽度
        
        main_layout.addWidget(splitter)
        
        # 底部状态栏
        self.statusBar = QStatusBar()
        self.statusBar.setStyleSheet("""
            QStatusBar {
                background: #f5f5f5;
                color: #666;
                font-size: 11px;
                border-top: 1px solid #e0e0e0;
                padding: 4px 8px;
            }
        """)
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("就绪")
        
    def create_toolbar(self):
        """创建顶部工具栏"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar {
                background: white;
                border-bottom: 1px solid #e0e0e0;
                padding: 6px 12px;
                spacing: 8px;
            }
            QLabel {
                color: #666;
                font-size: 12px;
                padding: 0 8px;
                font-weight: 500;
            }
            QComboBox {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 140px;
                background: white;
                font-size: 12px;
            }
            QComboBox:hover {
                border-color: #2196F3;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QPushButton {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 6px 14px;
                background: white;
                font-size: 12px;
                font-weight: 500;
            }
            QPushButton:hover {
                background: #f5f5f5;
                border-color: #2196F3;
            }
            QPushButton:pressed {
                background: #e3f2fd;
            }
        """)
        
        # 合集选择
        toolbar.addWidget(QLabel("合集:"))
        self.collection_combo = QComboBox()
        self.collection_combo.currentTextChanged.connect(self.on_collection_changed)
        toolbar.addWidget(self.collection_combo)
        
        toolbar.addSeparator()
        
        # 操作按钮
        new_collection_btn = QPushButton("➕ 新建合集")
        new_collection_btn.clicked.connect(self.create_new_collection)
        toolbar.addWidget(new_collection_btn)
        
        import_btn = QPushButton("📂 批量导入")
        import_btn.clicked.connect(self.batch_import)
        toolbar.addWidget(import_btn)
        
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.refresh_view)
        toolbar.addWidget(refresh_btn)
        
        # 添加弹性空间
        spacer = QWidget()
        spacer.setSizePolicy(QWidget.Policy.Expanding, QWidget.Policy.Preferred)
        toolbar.addWidget(spacer)
        
        # 删除合集按钮放在右侧
        delete_collection_btn = QPushButton("🗑️ 删除合集")
        delete_collection_btn.clicked.connect(self.delete_collection)
        delete_collection_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffebee;
                color: #c62828;
                border: 1px solid #ef9a9a;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #ffcdd2;
            }
            QPushButton:pressed {
                background-color: #ef9a9a;
            }
        """)
        toolbar.addWidget(delete_collection_btn)
        
        return toolbar
        
    def create_category_widget(self):
        """创建左侧类别选择组件"""
        widget = QWidget()
        widget.setStyleSheet("""
            QWidget {
                background: white;
                border-right: 1px solid #e0e0e0;
            }
        """)
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)
        
        # 标题
        title_label = QLabel("类别")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #333;
                padding: 4px 0;
            }
        """)
        layout.addWidget(title_label)
        
        # 搜索框
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("🔍 搜索类别...")
        self.search_box.textChanged.connect(self.filter_categories)
        self.search_box.setStyleSheet("""
            QLineEdit {
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px 12px;
                font-size: 12px;
                background: #fafafa;
            }
            QLineEdit:focus {
                border-color: #2196F3;
                background: white;
            }
        """)
        layout.addWidget(self.search_box)
        
        # 添加新建类别按钮
        new_category_btn = QPushButton("➕ 新建类别")
        new_category_btn.clicked.connect(self.create_new_category)
        new_category_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px;
                font-size: 12px;
                border: none;
                border-radius: 4px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
        """)
        layout.addWidget(new_category_btn)
        
        # 类别列表
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
        """)
        
        category_container = QWidget()
        category_container.setStyleSheet("background: transparent;")
        self.category_layout = QVBoxLayout(category_container)
        self.category_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.category_layout.setSpacing(4)
        
        scroll.setWidget(category_container)
        layout.addWidget(scroll)
        
        widget.setMaximumWidth(240)
        widget.setMinimumWidth(200)
        return widget
    
    def apply_light_theme(self):
        """应用亮色主题"""
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(250, 250, 250))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(33, 33, 33))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
        palette.setColor(QPalette.ColorRole.Text, QColor(33, 33, 33))
        palette.setColor(QPalette.ColorRole.Button, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(33, 33, 33))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(33, 150, 243))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        self.setPalette(palette)
    
    def show_toast(self, message: str, success=True):
        """显示Toast通知"""
        toast = Toast(message, self, success)
        
        # 计算位置（窗口底部中央）
        x = (self.width() - toast.width()) // 2
        y = self.height() - 100
        toast.move(x, y)
        
        toast.show_toast()
        
    def load_collections(self):
        """加载所有合集"""
        self.collection_combo.clear()
        
        if not self.sticker_base.exists():
            self.sticker_base.mkdir(parents=True, exist_ok=True)
            
        collections = [d.name for d in self.sticker_base.iterdir() if d.is_dir()]
        
        if collections:
            self.collection_combo.addItems(sorted(collections))
        else:
            self.show_toast("未找到表情包合集，请先创建一个合集", False)
            
    def on_collection_changed(self, collection_name: str):
        """切换合集"""
        if not collection_name:
            return
            
        self.current_collection = collection_name
        self.load_categories()
        self.update_stats()
        
    def load_categories(self):
        """加载当前合集的类别"""
        # 清空现有类别
        while self.category_layout.count():
            item = self.category_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.category_buttons = []
                
        if not self.current_collection:
            return
            
        collection_path = self.sticker_base / self.current_collection
        if not collection_path.exists():
            return
            
        categories = sorted([d.name for d in collection_path.iterdir() if d.is_dir()])
        
        for romaji_name in categories:
            chinese_name = CATEGORY_MAP.get(romaji_name, romaji_name)
            
            btn = QPushButton(f"{chinese_name}")
            btn.setProperty("romaji", romaji_name)
            btn.setProperty("chinese", chinese_name)
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, r=romaji_name, b=btn: self.on_category_selected(r, b))
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, r=romaji_name, b=btn: self.show_category_context_menu(pos, r, b)
            )
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 10px 12px;
                    border: none;
                    background-color: transparent;
                    color: #333;
                    font-size: 12px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #e3f2fd;
                }
                QPushButton:checked {
                    background-color: #2196F3;
                    color: white;
                    font-weight: bold;
                }
            """)
            
            # 显示该类别的图片数量
            category_path = collection_path / romaji_name
            count = len(list(category_path.glob("*.*")))
            btn.setText(f"{chinese_name} ({count})")
            
            self.category_layout.addWidget(btn)
            self.category_buttons.append(btn)
    
    def filter_categories(self, text: str):
        """过滤类别列表"""
        search_text = text.lower()
        
        for btn in self.category_buttons:
            chinese_name = btn.property("chinese")
            romaji_name = btn.property("romaji")
            
            # 搜索中文名或拼音
            if search_text in chinese_name.lower() or search_text in romaji_name.lower():
                btn.show()
            else:
                btn.hide()
            
    def on_category_selected(self, romaji_name: str, button: QPushButton):
        """选择类别"""
        # 取消其他按钮的选中状态
        for btn in self.category_buttons:
            if btn != button:
                btn.setChecked(False)
        
        button.setChecked(True)
        self.current_category = romaji_name
        self.load_stickers()
    
    def show_category_context_menu(self, pos: QPoint, romaji_name: str, button: QPushButton):
        """显示类别右键菜单"""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 24px;
                border-radius: 2px;
            }
            QMenu::item:selected {
                background: #e3f2fd;
            }
        """)
        
        delete_action = QAction("🗑️ 删除类别", self)
        delete_action.triggered.connect(lambda: self.delete_category(romaji_name))
        menu.addAction(delete_action)
        
        menu.exec(button.mapToGlobal(pos))
    
    def delete_category(self, romaji_name: str):
        """删除类别"""
        if not self.current_collection:
            return
        
        chinese_name = CATEGORY_MAP.get(romaji_name, romaji_name)
        category_path = self.sticker_base / self.current_collection / romaji_name
        
        # 统计该类别的文件数
        file_count = len(list(category_path.glob("*.*"))) if category_path.exists() else 0
        
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除类别 '{chinese_name}' 吗？\n"
            f"这将删除该类别下的 {file_count} 个表情包文件！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if category_path.exists():
                    shutil.rmtree(category_path)
                
                # 如果删除的是当前类别，清空显示
                if self.current_category == romaji_name:
                    self.current_category = None
                    while self.gallery_area.sticker_layout.count():
                        item = self.gallery_area.sticker_layout.takeAt(0)
                        if item.widget():
                            item.widget().deleteLater()
                
                self.load_categories()
                self.update_stats()
                self.show_toast(f"类别 '{chinese_name}' 已删除", True)
            except Exception as e:
                self.show_toast(f"删除失败", False)
    
    def get_next_filename(self, category_path: Path) -> str:
        """获取下一个文件名（自动编号）"""
        existing_files = list(category_path.glob("*.*"))
        if not existing_files:
            return "01"
        
        # 提取所有数字编号
        numbers = []
        for f in existing_files:
            match = re.match(r'^(\d+)', f.stem)
            if match:
                numbers.append(int(match.group(1)))
        
        if not numbers:
            return "01"
        
        # 返回下一个编号
        next_num = max(numbers) + 1
        return f"{next_num:02d}"
    
    def rename_files_in_category(self, category_path: Path):
        """重命名类别中的所有文件为连续编号"""
        if not category_path.exists():
            return
        
        existing_files = sorted(category_path.glob("*.*"), key=lambda x: x.stem)
        
        # 临时重命名以避免冲突
        temp_files = []
        for i, file_path in enumerate(existing_files, 1):
            temp_name = category_path / f"temp_{i}{file_path.suffix}"
            file_path.rename(temp_name)
            temp_files.append((temp_name, file_path.suffix))
        
        # 正式重命名为连续编号
        for i, (temp_path, suffix) in enumerate(temp_files, 1):
            final_name = category_path / f"{i:02d}{suffix}"
            temp_path.rename(final_name)
    
    def load_stickers(self):
        """加载当前类别的表情包"""
        # 清空现有表情包
        while self.gallery_area.sticker_layout.count():
            item = self.gallery_area.sticker_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        if not self.current_collection or not self.current_category:
            return
            
        category_path = self.sticker_base / self.current_collection / self.current_category
        if not category_path.exists():
            category_path.mkdir(parents=True, exist_ok=True)
            return
        
        # 确保文件名是连续编号的
        self.rename_files_in_category(category_path)
            
        # 支持的图片格式
        image_extensions = [".png", ".jpg", ".jpeg", ".gif", ".webp"]
        image_files = []
        for ext in image_extensions:
            image_files.extend(category_path.glob(f"*{ext}"))
            
        # 按文件名排序
        image_files = sorted(image_files, key=lambda x: x.stem)
        
        # 网格布局显示
        row, col = 0, 0
        max_cols = 4
        
        for image_path in image_files:
            widget = StickerWidget(image_path)
            widget.delete_clicked.connect(self.delete_sticker)
            self.gallery_area.sticker_layout.addWidget(widget, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
                
        # 更新状态栏
        chinese_name = CATEGORY_MAP.get(self.current_category, self.current_category)
        self.statusBar.showMessage(f"当前: {chinese_name} | 表情包: {len(image_files)} 个")
        
    def delete_sticker(self, file_path: str):
        """删除表情包"""
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除这个表情包吗？\n{Path(file_path).name}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                Path(file_path).unlink()
                
                # 重新加载并重新编号
                self.load_stickers()
                self.load_categories()
                
                self.show_toast("表情包已删除", True)
            except Exception as e:
                self.show_toast("删除失败", False)
                
    def handle_dropped_files(self, files):
        """处理拖放的文件"""
        if not self.current_collection or not self.current_category:
            self.show_toast("请先选择合集和类别", False)
            return
            
        category_path = self.sticker_base / self.current_collection / self.current_category
        category_path.mkdir(parents=True, exist_ok=True)
        
        success_count = 0
        fail_count = 0
        
        for file in files:
            try:
                # 获取下一个文件编号
                next_num = self.get_next_filename(category_path)
                
                if isinstance(file, QImage):
                    # 直接拖放的图片数据
                    dest_path = category_path / f"{next_num}.png"
                    file.save(str(dest_path))
                    success_count += 1
                elif isinstance(file, str):
                    if file.startswith(('http://', 'https://')):
                        # 网络URL
                        ext = Path(file).suffix or ".png"
                        dest_path = category_path / f"{next_num}{ext}"
                        urllib.request.urlretrieve(file, dest_path)
                        success_count += 1
                    else:
                        # 本地文件
                        source_path = Path(file)
                        if source_path.exists() and source_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                            dest_path = category_path / f"{next_num}{source_path.suffix}"
                            shutil.copy2(source_path, dest_path)
                            success_count += 1
                        else:
                            fail_count += 1
            except Exception as e:
                fail_count += 1
        
        # 重新编号所有文件
        self.rename_files_in_category(category_path)
        
        # 显示结果
        if success_count > 0:
            self.load_stickers()
            self.load_categories()
            self.show_toast(f"成功导入 {success_count} 个表情包", True)
        
        if fail_count > 0:
            self.show_toast(f"{fail_count} 个文件导入失败", False)
            
    def batch_import(self):
        """批量导入表情包"""
        if not self.current_collection or not self.current_category:
            self.show_toast("请先选择合集和类别", False)
            return
            
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "选择表情包文件",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.gif *.webp);;所有文件 (*.*)"
        )
        
        if files:
            self.handle_dropped_files(files)
            
    def create_new_collection(self):
        """创建新合集"""
        name, ok = QInputDialog.getText(self, "新建合集", "请输入合集名称:")
        
        if ok and name:
            collection_path = self.sticker_base / name
            if collection_path.exists():
                self.show_toast("该合集已存在", False)
                return
                
            try:
                collection_path.mkdir(parents=True, exist_ok=True)
                self.load_collections()
                self.collection_combo.setCurrentText(name)
                self.show_toast(f"合集 '{name}' 创建成功", True)
            except Exception as e:
                self.show_toast("创建失败", False)
    
    def create_new_category(self):
        """创建新类别"""
        if not self.current_collection:
            self.show_toast("请先选择合集", False)
            return
        
        # 创建一个对话框让用户选择或输入类别
        dialog = QDialog(self)
        dialog.setWindowTitle("新建类别")
        dialog.setMinimumWidth(450)
        dialog.setStyleSheet("""
            QDialog {
                background: white;
            }
            QLabel {
                color: #333;
                font-size: 12px;
            }
            QComboBox, QLineEdit {
                padding: 8px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 12px;
            }
            QComboBox:focus, QLineEdit:focus {
                border-color: #2196F3;
            }
        """)
        
        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)
        
        # 说明文字
        info_label = QLabel("请从列表中选择已定义的类别，或输入自定义类别名称：")
        info_label.setStyleSheet("font-weight: 500;")
        layout.addWidget(info_label)
        
        # 类别选择下拉框
        layout.addWidget(QLabel("预定义类别（中文）："))
        category_combo = QComboBox()
        category_combo.setStyleSheet("min-height: 32px;")
        
        # 添加所有映射的类别（按中文名排序）
        sorted_categories = sorted(CHINESE_TO_ROMAJI.items())
        category_combo.addItem("-- 选择预定义类别 --", "")
        for chinese, romaji in sorted_categories:
            category_combo.addItem(chinese, romaji)
        
        layout.addWidget(category_combo)
        
        # 自定义类别输入
        layout.addWidget(QLabel("或输入自定义类别名称（拼音）："))
        custom_input = QLineEdit()
        custom_input.setPlaceholderText("例如: custom_category")
        custom_input.setStyleSheet("min-height: 32px;")
        layout.addWidget(custom_input)
        
        # 提示信息
        hint_label = QLabel("提示：自定义类别将以拼音形式显示")
        hint_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(hint_label)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.setStyleSheet("""
            QPushButton {
                padding: 8px 20px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 500;
            }
        """)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 获取选择或输入的类别
            custom_name = custom_input.text().strip()
            selected_romaji = category_combo.currentData()
            
            category_romaji = custom_name if custom_name else selected_romaji
            
            if not category_romaji:
                self.show_toast("请选择或输入类别名称", False)
                return
            
            # 检查类别是否已存在
            category_path = self.sticker_base / self.current_collection / category_romaji
            if category_path.exists():
                self.show_toast(f"类别 '{category_romaji}' 已存在", False)
                return
            
            try:
                category_path.mkdir(parents=True, exist_ok=True)
                self.load_categories()
                chinese_name = CATEGORY_MAP.get(category_romaji, category_romaji)
                self.show_toast(f"类别 '{chinese_name}' 创建成功", True)
                
                # 自动选择新创建的类别
                self.current_category = category_romaji
                self.load_stickers()
            except Exception as e:
                self.show_toast("创建类别失败", False)
                
    def delete_collection(self):
        """删除合集"""
        if not self.current_collection:
            self.show_toast("请先选择要删除的合集", False)
            return
            
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除合集 '{self.current_collection}' 吗？\n这将删除该合集下的所有表情包！",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                collection_path = self.sticker_base / self.current_collection
                shutil.rmtree(collection_path)
                self.load_collections()
                self.show_toast(f"合集 '{self.current_collection}' 已删除", True)
            except Exception as e:
                self.show_toast("删除失败", False)
                
    def refresh_view(self):
        """刷新视图"""
        self.load_categories()
        if self.current_category:
            self.load_stickers()
        self.update_stats()
        self.show_toast("已刷新", True)
        
    def update_stats(self):
        """更新统计信息"""
        if not self.current_collection:
            self.statusBar.showMessage("就绪")
            return
            
        collection_path = self.sticker_base / self.current_collection
        if not collection_path.exists():
            return
            
        # 统计当前合集
        categories = [d for d in collection_path.iterdir() if d.is_dir()]
        total_stickers = 0
        
        for category in categories:
            total_stickers += len(list(category.glob("*.*")))
            
        # 统计所有合集
        all_collections = [d for d in self.sticker_base.iterdir() if d.is_dir()]
        all_stickers = 0
        
        for coll in all_collections:
            for category in coll.iterdir():
                if category.is_dir():
                    all_stickers += len(list(category.glob("*.*")))
                    
        stats_text = (
            f"合集: {self.current_collection} ({len(categories)} 类, {total_stickers} 图) | "
            f"总计: {len(all_collections)} 合集, {all_stickers} 图"
        )
        
        self.statusBar.showMessage(stats_text)


def main():
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    
    window = StickerManagerWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
