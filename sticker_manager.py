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
from pathlib import Path
from typing import Dict, List, Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QGridLayout, QScrollArea,
    QMessageBox, QInputDialog, QFileDialog, QDialog, QDialogButtonBox,
    QLineEdit, QGroupBox, QSplitter, QFrame, QMenu
)
from PyQt6.QtCore import Qt, QUrl, pyqtSignal, QMimeData, QPoint
from PyQt6.QtGui import QPixmap, QImage, QDragEnterEvent, QDropEvent, QAction

# 导入类别映射
from sticker_categories import CATEGORY_MAP, CHINESE_TO_ROMAJI


class StickerWidget(QFrame):
    """单个表情包的显示组件"""
    delete_clicked = pyqtSignal(str)  # 发送文件路径
    
    def __init__(self, image_path: Path, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 图片显示
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setFixedSize(150, 150)
        self.image_label.setStyleSheet("border: 1px solid #ddd; background: white;")
        
        # 加载图片
        pixmap = QPixmap(str(self.image_path))
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(
                140, 140,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
        
        # 文件名
        name_label = QLabel(self.image_path.name)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setWordWrap(True)
        name_label.setMaximumWidth(150)
        name_label.setStyleSheet("font-size: 10px;")
        
        # 删除按钮
        delete_btn = QPushButton("删除")
        delete_btn.setMaximumWidth(150)
        delete_btn.clicked.connect(lambda: self.delete_clicked.emit(str(self.image_path)))
        delete_btn.setStyleSheet("QPushButton { background-color: #ff4444; color: white; }")
        
        layout.addWidget(self.image_label)
        layout.addWidget(name_label)
        layout.addWidget(delete_btn)
        
        self.setLayout(layout)
        self.setFrameStyle(QFrame.Shape.Box)


class DropArea(QWidget):
    """支持拖放的区域"""
    files_dropped = pyqtSignal(list)  # 发送文件路径列表
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        label = QLabel("拖放图片到此处\n（支持本地文件和浏览器图片）")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                padding: 40px;
                background-color: #f5f5f5;
                font-size: 14px;
                color: #666;
            }
        """)
        layout.addWidget(label)
        self.setLayout(layout)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls() or event.mimeData().hasImage():
            event.acceptProposedAction()
            
    def dropEvent(self, event: QDropEvent):
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
        self.sticker_base = Path(__file__).parent / "data" / "stickers"
        self.current_collection = None
        self.current_category = None
        self.setup_ui()
        self.load_collections()
        
    def setup_ui(self):
        self.setWindowTitle("表情包管理工具")
        self.setMinimumSize(1000, 700)
        
        # 主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 顶部控制面板
        control_panel = self.create_control_panel()
        main_layout.addWidget(control_panel)
        
        # 分割器：左侧类别列表，右侧表情包展示
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 左侧类别选择
        category_widget = self.create_category_widget()
        splitter.addWidget(category_widget)
        
        # 右侧内容区域
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        # 拖放区域
        self.drop_area = DropArea()
        self.drop_area.files_dropped.connect(self.handle_dropped_files)
        right_layout.addWidget(self.drop_area)
        
        # 表情包展示区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        self.sticker_container = QWidget()
        self.sticker_layout = QGridLayout(self.sticker_container)
        self.sticker_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        scroll_area.setWidget(self.sticker_container)
        right_layout.addWidget(scroll_area)
        
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        
        main_layout.addWidget(splitter)
        
        # 底部统计信息
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("padding: 10px; background-color: #f0f0f0; font-size: 12px;")
        main_layout.addWidget(self.stats_label)
        
    def create_control_panel(self):
        """创建顶部控制面板"""
        panel = QGroupBox("合集管理")
        layout = QHBoxLayout()
        
        # 合集选择
        layout.addWidget(QLabel("当前合集:"))
        self.collection_combo = QComboBox()
        self.collection_combo.currentTextChanged.connect(self.on_collection_changed)
        layout.addWidget(self.collection_combo)
        
        # 合集操作按钮
        new_collection_btn = QPushButton("新建合集")
        new_collection_btn.clicked.connect(self.create_new_collection)
        layout.addWidget(new_collection_btn)
        
        delete_collection_btn = QPushButton("删除合集")
        delete_collection_btn.clicked.connect(self.delete_collection)
        delete_collection_btn.setStyleSheet("QPushButton { background-color: #ff6666; color: white; }")
        layout.addWidget(delete_collection_btn)
        
        layout.addStretch()
        
        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.refresh_view)
        layout.addWidget(refresh_btn)
        
        # 批量导入按钮
        import_btn = QPushButton("批量导入")
        import_btn.clicked.connect(self.batch_import)
        layout.addWidget(import_btn)
        
        panel.setLayout(layout)
        return panel
        
    def create_category_widget(self):
        """创建左侧类别选择组件"""
        widget = QGroupBox("类别")
        layout = QVBoxLayout()
        
        # 添加新建类别按钮
        new_category_btn = QPushButton("➕ 新建类别")
        new_category_btn.clicked.connect(self.create_new_category)
        new_category_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        layout.addWidget(new_category_btn)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        category_container = QWidget()
        self.category_layout = QVBoxLayout(category_container)
        self.category_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        scroll.setWidget(category_container)
        layout.addWidget(scroll)
        
        widget.setLayout(layout)
        widget.setMaximumWidth(250)
        return widget
        
    def load_collections(self):
        """加载所有合集"""
        self.collection_combo.clear()
        
        if not self.sticker_base.exists():
            self.sticker_base.mkdir(parents=True, exist_ok=True)
            
        collections = [d.name for d in self.sticker_base.iterdir() if d.is_dir()]
        
        if collections:
            self.collection_combo.addItems(sorted(collections))
        else:
            QMessageBox.information(self, "提示", "未找到表情包合集，请先创建一个合集。")
            
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
            btn.setCheckable(True)  # 允许按钮保持选中状态
            btn.clicked.connect(lambda checked, r=romaji_name, b=btn: self.on_category_selected(r, b))
            btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, r=romaji_name, b=btn: self.show_category_context_menu(pos, r, b)
            )
            btn.setStyleSheet("""
                QPushButton {
                    text-align: left;
                    padding: 8px;
                    border: 1px solid #ddd;
                    background-color: white;
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
            
    def on_category_selected(self, romaji_name: str, button: QPushButton):
        """选择类别"""
        # 取消其他按钮的选中状态
        for i in range(self.category_layout.count()):
            item = self.category_layout.itemAt(i)
            if item and item.widget() and item.widget() != button:
                widget = item.widget()
                if isinstance(widget, QPushButton):
                    widget.setChecked(False)
        
        button.setChecked(True)
        self.current_category = romaji_name
        self.load_stickers()
    
    def show_category_context_menu(self, pos: QPoint, romaji_name: str, button: QPushButton):
        """显示类别右键菜单"""
        menu = QMenu(self)
        
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
                    while self.sticker_layout.count():
                        item = self.sticker_layout.takeAt(0)
                        if item.widget():
                            item.widget().deleteLater()
                
                self.load_categories()
                self.update_stats()
                QMessageBox.information(self, "成功", f"类别 '{chinese_name}' 已删除")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")
        
    def load_stickers(self):
        """加载当前类别的表情包"""
        # 清空现有表情包
        while self.sticker_layout.count():
            item = self.sticker_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        if not self.current_collection or not self.current_category:
            return
            
        category_path = self.sticker_base / self.current_collection / self.current_category
        if not category_path.exists():
            category_path.mkdir(parents=True, exist_ok=True)
            return
            
        # 支持的图片格式
        image_extensions = [".png", ".jpg", ".jpeg", ".gif", ".webp"]
        image_files = []
        for ext in image_extensions:
            image_files.extend(category_path.glob(f"*{ext}"))
            
        # 按文件名排序
        image_files = sorted(image_files)
        
        # 网格布局显示
        row, col = 0, 0
        max_cols = 4
        
        for image_path in image_files:
            widget = StickerWidget(image_path)
            widget.delete_clicked.connect(self.delete_sticker)
            self.sticker_layout.addWidget(widget, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
                
        # 更新统计
        chinese_name = CATEGORY_MAP.get(self.current_category, self.current_category)
        self.stats_label.setText(f"当前类别: {chinese_name} | 表情包数量: {len(image_files)}")
        
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
                self.load_stickers()
                self.load_categories()
                QMessageBox.information(self, "成功", "表情包已删除")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")
                
    def handle_dropped_files(self, files):
        """处理拖放的文件"""
        if not self.current_collection or not self.current_category:
            QMessageBox.warning(self, "警告", "请先选择合集和类别")
            return
            
        category_path = self.sticker_base / self.current_collection / self.current_category
        category_path.mkdir(parents=True, exist_ok=True)
        
        success_count = 0
        timestamp = int(time.time() * 1000)  # 使用时间戳避免重复扫描目录
        
        for idx, file in enumerate(files):
            try:
                if isinstance(file, QImage):
                    # 直接拖放的图片数据
                    dest_path = category_path / f"dropped_{timestamp}_{idx}.png"
                    file.save(str(dest_path))
                    success_count += 1
                elif isinstance(file, str):
                    if file.startswith(('http://', 'https://')):
                        # 网络URL
                        filename = Path(file).name or f"download_{timestamp}_{idx}.png"
                        dest_path = category_path / filename
                        urllib.request.urlretrieve(file, dest_path)
                        success_count += 1
                    else:
                        # 本地文件
                        source_path = Path(file)
                        if source_path.exists() and source_path.suffix.lower() in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                            dest_path = category_path / source_path.name
                            shutil.copy2(source_path, dest_path)
                            success_count += 1
            except Exception as e:
                # 记录错误但使用简化的错误消息
                error_msg = f"导入失败"
                if isinstance(file, str):
                    file_name = Path(file).name if len(file) < 100 else Path(file).name[:50] + "..."
                    error_msg = f"导入失败: {file_name}"
                QMessageBox.warning(self, "警告", error_msg)
                
        if success_count > 0:
            QMessageBox.information(self, "成功", f"成功导入 {success_count} 个表情包")
            self.load_stickers()
            self.load_categories()
            
    def batch_import(self):
        """批量导入表情包"""
        if not self.current_collection or not self.current_category:
            QMessageBox.warning(self, "警告", "请先选择合集和类别")
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
                QMessageBox.warning(self, "警告", "该合集已存在")
                return
                
            try:
                collection_path.mkdir(parents=True, exist_ok=True)
                self.load_collections()
                self.collection_combo.setCurrentText(name)
                QMessageBox.information(self, "成功", f"合集 '{name}' 创建成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建失败: {str(e)}")
    
    def create_new_category(self):
        """创建新类别"""
        if not self.current_collection:
            QMessageBox.warning(self, "警告", "请先选择合集")
            return
        
        # 创建一个对话框让用户选择或输入类别
        dialog = QDialog(self)
        dialog.setWindowTitle("新建类别")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # 说明文字
        info_label = QLabel("请从列表中选择已定义的类别，或输入自定义类别名称：")
        layout.addWidget(info_label)
        
        # 类别选择下拉框
        layout.addWidget(QLabel("预定义类别（中文）："))
        category_combo = QComboBox()
        
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
        layout.addWidget(custom_input)
        
        # 提示信息
        hint_label = QLabel("提示：自定义类别将以拼音形式显示")
        hint_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(hint_label)
        
        # 按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # 获取选择或输入的类别
            custom_name = custom_input.text().strip()
            selected_romaji = category_combo.currentData()
            
            category_romaji = custom_name if custom_name else selected_romaji
            
            if not category_romaji:
                QMessageBox.warning(self, "警告", "请选择或输入类别名称")
                return
            
            # 检查类别是否已存在
            category_path = self.sticker_base / self.current_collection / category_romaji
            if category_path.exists():
                QMessageBox.warning(self, "警告", f"类别 '{category_romaji}' 已存在")
                return
            
            try:
                category_path.mkdir(parents=True, exist_ok=True)
                self.load_categories()
                chinese_name = CATEGORY_MAP.get(category_romaji, category_romaji)
                QMessageBox.information(
                    self, "成功", 
                    f"类别 '{chinese_name}' ({category_romaji}) 创建成功"
                )
                # 自动选择新创建的类别
                self.current_category = category_romaji
                self.load_stickers()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"创建类别失败: {str(e)}")
                
                
    def delete_collection(self):
        """删除合集"""
        if not self.current_collection:
            QMessageBox.warning(self, "警告", "请先选择要删除的合集")
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
                QMessageBox.information(self, "成功", f"合集 '{self.current_collection}' 已删除")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")
                
    def refresh_view(self):
        """刷新视图"""
        self.load_categories()
        if self.current_category:
            self.load_stickers()
        self.update_stats()
        
    def update_stats(self):
        """更新统计信息"""
        if not self.current_collection:
            self.stats_label.setText("统计信息: 未选择合集")
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
            f"当前合集: {self.current_collection} | "
            f"类别数: {len(categories)} | "
            f"表情包数: {total_stickers} || "
            f"总合集数: {len(all_collections)} | "
            f"总表情包数: {all_stickers}"
        )
        
        self.stats_label.setText(stats_text)


def main():
    app = QApplication(sys.argv)
    
    # 设置应用样式
    app.setStyle("Fusion")
    
    window = StickerManagerWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
