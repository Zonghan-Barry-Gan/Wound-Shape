from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QTreeWidgetItem, QLineEdit
from PyQt6.QtCore import QDir, Qt, QEvent, QPoint, QSize
from PyQt6.QtGui import QImage, QPixmap, QPainter, QKeySequence, QShortcut
from generationFile.mainWindow_ui import Ui_MainWindow
import cv2
import sys
import os
import numpy as np


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # 成员变量
        self.m_folderPath = "./data"
        self.srcImgs = {}  # key: imgName, value: img
        self.dstImgs = {}  # key: imgName, value: img
        self.cornersPts = {}  # key: imgName, value: pts
        self.grid_dict = {}  # key: imgName, value: grid_dict

        # 缩放相关变量
        self.src_scale = 1.0
        self.dst_scale = 1.0
        # 拖动相关变量
        self.src_drag_start = None
        self.dst_drag_start = None
        self.src_offset = QPoint(0, 0)
        self.dst_offset = QPoint(0, 0)
        # 模式相关变量
        self.mode = "normal"  # normal, get_grid_points, delete_grid_points
        self.lasso_points = []  # 用于存储套索点
        # 初始化UI
        self.initUI()
        self.openFolder()
        self.statusBar().showMessage("正常模式")

        self.load_grid_dict()

    def initUI(self):
        self.setWindowTitle('网络点提取')

        # self.setFixedSize(1080, 720)
        self.ui.m_imgTreeWidget.setHeaderLabels(["文件名"])
        self.ui.m_imgTreeWidget.header().setDefaultAlignment(
            Qt.AlignmentFlag.AlignCenter)                      # 设置表头居中
        self.ui.m_imgTreeWidget.setAlternatingRowColors(True)  # 设置交替行颜色
        self.ui.m_imgTreeWidget.expandAll()  # 默认展开所有项

        # 信号与槽
        self.ui.m_openFolderAction.triggered.connect(self.openFolder)
        self.ui.m_imgTreeWidget.itemClicked.connect(self.onTreeItemClicked)
        self.ui.m_processImgBtn.clicked.connect(
            self.processCurrentImage)  # 添加处理按钮信号连接
        self.ui.m_getGridCornersBtn.clicked.connect(
            self.startGetGridPoints)  # 获取网格点按钮
        self.ui.m_deleteGridCornersBtn.clicked.connect(
            self.startDeleteGridPoints)  # 删除网格点按钮
        self.ui.m_manualGridIndexBtn.clicked.connect(
            self.manualGridPointsIndex)  # 手动编号按钮
        self.ui.m_finishGridCornersBtn.clicked.connect(
            self.finishGridPoints)  # 完成按钮
        self.ui.m_saveImgBtn.clicked.connect(self.saveGridPoints)  # 保存所有按钮
        self.ui.m_saveCurrentImgBtn.clicked.connect(
            self.saveCurrentImageGridPoints)  # 保存当前图片按钮

        # 为图像标签安装事件过滤器
        self.ui.m_srcImgLabel.installEventFilter(self)
        self.ui.m_dstImgLabel.installEventFilter(self)

        # 设置快捷键
        self.setupShortcuts()

        # 设置焦点策略，使窗口能接收键盘事件
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def setupShortcuts(self):
        """设置快捷键"""
        # A键 - 获取网格点
        shortcut_a = QShortcut(QKeySequence('A'), self)
        shortcut_a.activated.connect(self.startGetGridPoints)

        # D键 - 删除网格点
        shortcut_d = QShortcut(QKeySequence('D'), self)
        shortcut_d.activated.connect(self.startDeleteGridPoints)

        # W键 - 完成操作
        shortcut_w = QShortcut(QKeySequence('W'), self)
        shortcut_w.activated.connect(self.finishGridPoints)

        # S键 - 保存当前图片
        shortcut_s = QShortcut(QKeySequence('S'), self)
        shortcut_s.activated.connect(self.saveCurrentImageGridPoints)

        # Page Up - 上一张图片
        shortcut_pageup = QShortcut(QKeySequence(Qt.Key.Key_PageUp), self)
        shortcut_pageup.activated.connect(self.previousImage)

        # Page Down - 下一张图片
        shortcut_pagedown = QShortcut(QKeySequence(Qt.Key.Key_PageDown), self)
        shortcut_pagedown.activated.connect(self.nextImage)

    def previousImage(self):
        """切换到上一张图片"""
        current_item = self.ui.m_imgTreeWidget.currentItem()
        if not current_item or not current_item.parent() or current_item.parent().text(0) != "src":
            return

        # 获取src文件夹节点
        src_node = current_item.parent()
        current_index = src_node.indexOfChild(current_item)

        if current_index > 0:
            # 选择上一张图片
            prev_item = src_node.child(current_index - 1)
            self.ui.m_imgTreeWidget.setCurrentItem(prev_item)
            self.onTreeItemClicked(prev_item, 0)

    def nextImage(self):
        """切换到下一张图片"""
        current_item = self.ui.m_imgTreeWidget.currentItem()
        if not current_item or not current_item.parent() or current_item.parent().text(0) != "src":
            return

        # 获取src文件夹节点
        src_node = current_item.parent()
        current_index = src_node.indexOfChild(current_item)

        if current_index < src_node.childCount() - 1:
            # 选择下一张图片
            next_item = src_node.child(current_index + 1)
            self.ui.m_imgTreeWidget.setCurrentItem(next_item)
            self.onTreeItemClicked(next_item, 0)

    def processCurrentImage(self):
        # """处理当前选中的图像"""
        # current_item = self.ui.m_imgTreeWidget.currentItem()
        # if not current_item or not current_item.parent() or current_item.parent().text(0) != "src":
        #     return
        # img_name = current_item.text(0)
        # src_img = self.srcImgs.get(img_name)

        HMax = self.ui.m_HSVslider_H1.value()
        VMax = self.ui.m_HSVslider_V1.value()
        SMax = self.ui.m_HSVslider_S1.value()
        HMin = self.ui.m_HSVslider_H2.value()
        SMin = self.ui.m_HSVslider_S2.value()
        VMin = self.ui.m_HSVslider_V2.value()
        HMin, HMax = sorted([HMin, HMax])
        VMin, VMax = sorted([VMin, VMax])
        SMin, SMax = sorted([SMin, SMax])
        print(HMin, SMin, VMin)
        print(HMax, SMax, VMax)

        # 对所有self.srcImgs图像进行处理
        for img_name, src_img in self.srcImgs.items():
            src_img = self.srcImgs[img_name]
            if src_img is not None:
                # 3 * 3 等分 截取中心区域
                rows, cols, _ = src_img.shape
                row_div = rows // 3
                col_div = cols // 3
                row_start = row_div + 1
                row_end = 2 * row_div
                col_start = col_div + 1
                col_end = 2 * col_div
                row_start = max(0, row_start - 200)
                row_end = min(rows, row_end + 200)
                col_start = max(0, col_start-200)
                col_end = min(cols, col_end+200)
                mid_region = src_img[row_start:row_end, col_start:col_end]
                # 转到hsv颜色空间
                hsv = cv2.cvtColor(mid_region, cv2.COLOR_BGR2HSV)
                # 提取黑色的圆斑点
                # lower_black = (HMin, SMin, VMin)
                # upper_black = (HMax, SMax, VMax)
                lower_black = (0, 0, 0)
                upper_black = (180, 255, 35)
                mask_black = cv2.inRange(hsv, lower_black, upper_black)

                kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (25, 25))
                mask_black = cv2.morphologyEx(
                    mask_black, cv2.MORPH_CLOSE, kernel)

                # 提取轮廓,计算面积, 剔除过大过小的轮廓
                contours, _ = cv2.findContours(
                    mask_black, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

                area_min = 500
                area_max = 10000
                filtered_contours = [cnt for cnt in contours if cv2.contourArea(
                    cnt) > area_min and cv2.contourArea(cnt) < area_max]

                print("筛选后的轮廓数量:", len(filtered_contours))

                # 计算每个轮廓的质心
                centroids = [cv2.moments(cnt) for cnt in filtered_contours]
                centroids = [(int(M['m10'] / M['m00']), int(M['m01'] / M['m00']))
                             for M in centroids]

                # 计算每个轮廓最小外接矩形的最大边
                diameter = [max(cv2.minAreaRect(cnt)[1])
                            for cnt in filtered_contours]

                # 绘制轮廓
                mask_black_color = cv2.cvtColor(mask_black, cv2.COLOR_GRAY2BGR)
                cv2.drawContours(mask_black_color,
                                 filtered_contours, -1, (0, 255, 0), 2)

                # 绘制质心
                for centroid in centroids:
                    cv2.circle(mask_black_color, centroid, 5, (0, 0, 255), -1)

                lower_cyan = (70, 43, 46)
                upper_cyan = (99, 255, 255)
                mask_cyan = cv2.inRange(hsv, lower_cyan, upper_cyan)

                # 计算每个质心区域青色像素占比
                valid_centroids = []
                for i, centroid in enumerate(centroids):
                    radius = int(diameter[i] / 2 * 1.25)
                    circle = np.zeros_like(mask_cyan)
                    cv2.circle(circle, centroid, radius, 255, -1)
                    masked = cv2.bitwise_and(mask_cyan, mask_cyan, mask=circle)
                    cyan_area = cv2.countNonZero(masked)
                    total_area = cv2.countNonZero(circle)

                    if total_area > 0 and cyan_area / total_area > 0.02:
                        valid_centroids.append(centroid)
                    else:
                        print(
                            f"轮廓 {i}  的青色像素: {cyan_area}, 总像素: {total_area} , 占比：{cyan_area / total_area * 100:.2f}%")

                # 更新质心列表为有效质心
                print("有效质心数量:", len(valid_centroids))

                self.cornersPts[img_name] = [
                    QPoint(x + col_start, y + row_start) for x, y in valid_centroids]

                self.grid_dict[img_name] = self.organizeGridPoints(
                    self.cornersPts[img_name])

                # 更新dstImgs
                self.dstImgs[img_name] = mask_black_color

            self.updateSrcImage(isOrganize=True)
            self.updateDstImage()
            self.statusBar().showMessage(f"已处理完成")

    def onTreeItemClicked(self, item, column):
        # 检查是否点击的是src文件夹下的图片项
        parent = item.parent()
        if parent is None or parent.text(0) != "src":
            return

        # 清除可能存在的文本控件
        if hasattr(self, 'grid_text_edits'):
            for text_edit in self.grid_text_edits.values():
                text_edit.deleteLater()
            self.grid_text_edits = {}

        self.ui.m_srcImgLabel.clear()
        self.ui.m_dstImgLabel.clear()
        # 重置缩放和偏移
        self.src_scale = 1.0
        self.dst_scale = 1.0
        self.src_offset = QPoint(0, 0)
        self.dst_offset = QPoint(0, 0)
        self.src_drag_start = None
        self.dst_drag_start = None

        # 重置模式状态
        self.mode = "normal"
        self.lasso_points = []
        self.statusBar().showMessage("正常模式")

        # 确保当前图片在cornersPts中有记录
        img_name = item.text(0)
        if img_name not in self.cornersPts:
            self.cornersPts[img_name] = []

        # 使用updateSrcImage和updateDstImage方法来显示图像和网格点
        self.updateSrcImage()
        self.updateDstImage()

    def openFolder(self):
        # folder = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
        # folder = "./data"
        folder = self.m_folderPath
        if folder:
            self.loadImages(folder)

    def loadImages(self, folder_path):
        self.ui.m_imgTreeWidget.clear()
        self.srcImgs.clear()
        self.dstImgs.clear()
        self.cornersPts.clear()

        image_exts = ('.jpg', '.JPG', '.jpeg', '.png', '.bmp', '.gif')
        src_folder = os.path.join(folder_path, 'src')
        dst_folder = os.path.join(folder_path, 'dst')
        points_folder = os.path.join(folder_path, 'points')

        # 创建points文件夹（如果不存在）
        if not os.path.exists(points_folder):
            os.makedirs(points_folder)

        # 创建src文件夹节点
        src_item = QTreeWidgetItem(self.ui.m_imgTreeWidget)
        src_item.setText(0, "src")
        src_item.setExpanded(True)  # 展开节点

        # 加载src文件夹中的图片
        if os.path.exists(src_folder):
            src_files = os.listdir(src_folder)
            for file_name in src_files:
                if os.path.splitext(file_name)[1].lower() in image_exts:
                    img_path = os.path.join(src_folder, file_name)
                    img = cv2.imread(img_path)
                    if img is not None:
                        self.srcImgs[file_name] = img
                        # 将图片项添加为src文件夹的子项
                        item = QTreeWidgetItem(src_item)
                        item.setText(0, file_name)

                        # 为每张图片初始化空的网格点列表
                        self.cornersPts[file_name] = []

                        # 尝试加载网格点数据
                        points_file = os.path.join(
                            points_folder, f"{os.path.splitext(file_name)[0]}_points.txt")
                        if os.path.exists(points_file):
                            with open(points_file, 'r') as f:
                                for line in f:
                                    if line.strip():
                                        x, y = map(
                                            int, line.strip().split(','))
                                        self.cornersPts[file_name].append(
                                            QPoint(x, y))

        # 创建dst文件夹节点
        dst_item = QTreeWidgetItem(self.ui.m_imgTreeWidget)
        dst_item.setText(0, "dst")

        # 加载dst文件夹中的图片
        if os.path.exists(dst_folder):
            dst_files = os.listdir(dst_folder)
            if not dst_files:  # dst文件夹为空
                self.dstImgs = self.srcImgs.copy()  # 使用src的图片初始化
            else:
                for file_name in dst_files:
                    if os.path.splitext(file_name)[1].lower() in image_exts:
                        img_path = os.path.join(dst_folder, file_name)
                        img = cv2.imread(img_path)
                        if img is not None:
                            self.dstImgs[file_name] = img
                            # 将图片项添加为dst文件夹的子项
                            item = QTreeWidgetItem(dst_item)
                            item.setText(0, file_name)

    # 开始获取网格点模式

    def startGetGridPoints(self):
        self.mode = "get_grid_points"
        self.statusBar().showMessage("获取网格点模式：点击图像添加网格点")

    # 开始删除网格点模式
    def startDeleteGridPoints(self):
        self.mode = "delete_grid_points"
        self.lasso_points = []
        self.statusBar().showMessage("删除网格点模式：拖动鼠标画套索删除网格点")

    # 完成网格点操作
    def finishGridPoints(self):
        # 如果是手动编号模式，保存编辑的网格点编号
        if self.mode == "manual_grid_index" and hasattr(self, 'grid_text_edits'):
            current_item = self.ui.m_imgTreeWidget.currentItem()
            if current_item and current_item.parent() and current_item.parent().text(0) == "src":
                img_name = current_item.text(0)

                # 创建新的网格字典
                new_grid_dict = {}

                # 遍历所有文本控件，获取编辑后的编号
                for point, text_edit in self.grid_text_edits.items():
                    try:
                        # 获取编辑后的索引（格式为"行,列"）
                        index_str = text_edit.text()
                        # 将索引添加到新的网格字典
                        new_grid_dict[index_str] = point
                    except ValueError:
                        # 如果输入的不是有效索引，忽略该点
                        pass

                # 更新网格字典
                if img_name not in self.grid_dict:
                    self.grid_dict[img_name] = {}
                self.grid_dict[img_name] = new_grid_dict

                # 清除文本控件
                for text_edit in self.grid_text_edits.values():
                    text_edit.deleteLater()
                self.grid_text_edits = {}

                self.statusBar().showMessage(f"已保存手动编辑的网格点编号")

        # 恢复正常模式
        self.mode = "normal"
        self.lasso_points = []
        self.statusBar().showMessage("正常模式")

        # 更新图像显示
        self.updateSrcImage()

    # 保存网格点数据（所有图片）
    def saveGridPoints(self):
        # 创建保存文件夹
        points_folder = os.path.join(self.m_folderPath, 'points')
        if not os.path.exists(points_folder):
            os.makedirs(points_folder)

        # 创建gridDict文件夹
        grid_dict_folder = os.path.join(self.m_folderPath, 'gridDict')
        if not os.path.exists(grid_dict_folder):
            os.makedirs(grid_dict_folder)

        # 保存所有图片的网格点和grid_dict
        saved_count = 0
        for img_name in self.srcImgs.keys():
            # 保存cornersPts
            self.save_single_image_points(img_name, points_folder)

            # 处理cornersPts生成grid_dict并保存
            self.save_single_image_grid_dict(img_name, grid_dict_folder)

            saved_count += 1

        if saved_count > 0:
            self.statusBar().showMessage(f"已保存 {saved_count} 张图片的网格点数据和网格字典")
        else:
            self.statusBar().showMessage("没有图片需要保存网格点数据")

    # 保存当前选中图片的网格点数据
    def saveCurrentImageGridPoints(self):
        # 创建保存文件夹
        points_folder = os.path.join(self.m_folderPath, 'points')
        if not os.path.exists(points_folder):
            os.makedirs(points_folder)

        # 创建gridDict文件夹
        grid_dict_folder = os.path.join(self.m_folderPath, 'gridDict')
        if not os.path.exists(grid_dict_folder):
            os.makedirs(grid_dict_folder)

        # 获取当前选中的图片
        current_item = self.ui.m_imgTreeWidget.currentItem()

        # 如果有选中的图片，只保存当前图片的网格点
        if current_item and current_item.parent() and current_item.parent().text(0) == "src":
            img_name = current_item.text(0)
            # 保存cornersPts
            self.save_single_image_points(img_name, points_folder)

            # 处理cornersPts生成grid_dict并保存
            self.save_single_image_grid_dict(img_name, grid_dict_folder)

            self.statusBar().showMessage(f"已保存当前图片 {img_name} 的网格点数据和网格字典")
        else:
            self.statusBar().showMessage("没有选中有效的图片，无法保存网格点数据")

    # 保存单张图片的网格点

    def save_single_image_points(self, img_name, points_folder):
        file_path = os.path.join(
            points_folder, f"{os.path.splitext(img_name)[0]}_points.txt")

        # 即使没有网格点，也创建空文件
        with open(file_path, 'w') as f:
            if img_name in self.cornersPts and self.cornersPts[img_name]:
                for point in self.cornersPts[img_name]:
                    f.write(f"{point.x()},{point.y()}\n")

        # 如果是当前选中的图片，更新状态栏
        current_item = self.ui.m_imgTreeWidget.currentItem()
        if current_item and current_item.text(0) == img_name:
            if img_name in self.cornersPts and self.cornersPts[img_name]:
                self.statusBar().showMessage(
                    f"已保存 {len(self.cornersPts[img_name])} 个网格点到 {file_path}")
            else:
                self.statusBar().showMessage(f"已创建空的网格点文件 {file_path}")

    # 保存单张图片的网格字典
    def save_single_image_grid_dict(self, img_name, grid_dict_folder):
        file_path = os.path.join(
            grid_dict_folder, f"{os.path.splitext(img_name)[0]}_grid_dict.txt")

        # 处理cornersPts生成grid_dict
        if img_name in self.cornersPts:
            # grid_dict = self.organizeGridPoints(self.cornersPts[img_name])
            grid_dict = self.grid_dict[img_name]
            # 即使没有网格字典，也创建空文件
            with open(file_path, 'w') as f:
                if grid_dict:
                    for key, point in grid_dict.items():
                        # 保存格式：行索引,列索引,x坐标,y坐标
                        row_idx, col_idx = key.split(',')
                        f.write(
                            f"{row_idx},{col_idx},{point.x()},{point.y()}\n")

            # 如果是当前选中的图片，更新状态栏
            current_item = self.ui.m_imgTreeWidget.currentItem()
            if current_item and current_item.text(0) == img_name:
                if grid_dict:
                    self.statusBar().showMessage(
                        f"已保存 {len(grid_dict)} 个网格字典点到 {file_path}")
                else:
                    self.statusBar().showMessage(f"已创建空的网格字典文件 {file_path}")

    # 显示坐标转换为原图坐标

    def display_to_original_coords(self, display_point, label_size, img_shape, scale, offset):
        # 计算图像在标签中的位置
        img_h, img_w = img_shape[:2]
        scale_w = label_size.width() / img_w
        scale_h = label_size.height() / img_h
        base_scale = min(scale_w, scale_h) * scale

        # 计算缩放后的图像尺寸
        scaled_w = int(img_w * base_scale)
        scaled_h = int(img_h * base_scale)

        # 计算图像在标签中的位置
        x_offset = (label_size.width() - scaled_w) // 2 + offset.x()
        y_offset = (label_size.height() - scaled_h) // 2 + offset.y()

        # 将显示坐标转换为缩放后图像上的坐标
        img_x = display_point.x() - x_offset
        img_y = display_point.y() - y_offset

        # 将缩放后图像上的坐标转换为原图坐标
        original_x = int(img_x / base_scale)
        original_y = int(img_y / base_scale)

        # 确保坐标在原图范围内
        original_x = max(0, min(original_x, img_w - 1))
        original_y = max(0, min(original_y, img_h - 1))

        return QPoint(original_x, original_y)

    # 判断点是否在多边形内部
    def point_in_polygon(self, point, polygon):
        if len(polygon) < 3:
            return False

        n = len(polygon)
        inside = False
        p1x, p1y = polygon[0].x(), polygon[0].y()

        for i in range(n + 1):
            p2x, p2y = polygon[i % n].x(), polygon[i % n].y()
            if point.y() > min(p1y, p2y):
                if point.y() <= max(p1y, p2y):
                    if point.x() <= max(p1x, p2x):
                        if p1y != p2y:
                            xinters = (point.y() - p1y) * \
                                (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or point.x() <= xinters:
                            inside = not inside
            p1x, p1y = p2x, p2y

        return inside

    def eventFilter(self, obj, event):
        if obj in [self.ui.m_srcImgLabel, self.ui.m_dstImgLabel]:
            # 只处理src图像标签的事件
            if obj == self.ui.m_srcImgLabel:
                # 获取当前选中的图像名称
                current_item = self.ui.m_imgTreeWidget.currentItem()
                if not current_item or not current_item.parent() or current_item.parent().text(0) != "src":
                    return super().eventFilter(obj, event)

                img_name = current_item.text(0)
                src_img = self.srcImgs.get(img_name)
                if src_img is None:
                    return super().eventFilter(obj, event)

                # 处理不同模式下的事件
                if self.mode == "get_grid_points":
                    # 获取网格点模式
                    if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                        # 获取点击位置
                        click_pos = event.position().toPoint()
                        # 转换为原图坐标
                        label_size = self.ui.m_srcImgLabel.size()
                        original_pos = self.display_to_original_coords(
                            click_pos, label_size, src_img.shape, self.src_scale, self.src_offset)

                        # 初始化cornersPts字典
                        if img_name not in self.cornersPts:
                            self.cornersPts[img_name] = []

                        # 添加网格点
                        self.cornersPts[img_name].append(original_pos)
                        self.statusBar().showMessage(
                            f"添加网格点: ({original_pos.x()}, {original_pos.y()})")

                        # 更新图像显示
                        self.updateSrcImage(isOrganize=True)
                        return True

                elif self.mode == "delete_grid_points":
                    # 删除网格点模式
                    if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                        # 开始绘制套索
                        self.lasso_points = [event.position().toPoint()]
                        return True

                    elif event.type() == QEvent.Type.MouseMove and self.lasso_points:
                        # 继续绘制套索
                        self.lasso_points.append(event.position().toPoint())
                        # 更新图像显示
                        self.updateSrcImage()
                        return True

                    elif event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton and self.lasso_points:
                        # 完成套索绘制，删除套索内的点
                        if img_name in self.cornersPts and len(self.cornersPts[img_name]) > 0:
                            # 获取标签大小和图像信息
                            label_size = self.ui.m_srcImgLabel.size()

                            # 转换套索点为原图坐标系中的多边形
                            lasso_polygon = []
                            for point in self.lasso_points:
                                lasso_polygon.append(self.display_to_original_coords(
                                    point, label_size, src_img.shape, self.src_scale, self.src_offset))

                            # 找出在套索内的点
                            points_to_remove = []
                            for i, point in enumerate(self.cornersPts[img_name]):
                                if self.point_in_polygon(point, lasso_polygon):
                                    points_to_remove.append(i)

                            # 从后往前删除点，避免索引变化
                            for i in sorted(points_to_remove, reverse=True):
                                del self.cornersPts[img_name][i]

                            self.statusBar().showMessage(
                                f"删除了 {len(points_to_remove)} 个网格点")

                        # 清空套索点
                        self.lasso_points = []
                        # 更新图像显示
                        self.updateSrcImage(isOrganize=True)
                        return True

            # 处理滚轮缩放
            if event.type() == QEvent.Type.Wheel:
                # 计算缩放因子
                factor = 1.1 if event.angleDelta().y() > 0 else 0.9

                if obj == self.ui.m_srcImgLabel:
                    self.src_scale *= factor
                    self.updateSrcImage()
                else:
                    self.dst_scale *= factor
                    self.updateDstImage()
                return True

            # 处理鼠标按下事件 (正常模式下的左键拖动和任何模式下的中键拖动)
            elif event.type() == QEvent.Type.MouseButtonPress:
                if (event.button() == Qt.MouseButton.LeftButton and self.mode == "normal") or event.button() == Qt.MouseButton.MiddleButton:
                    if obj == self.ui.m_srcImgLabel:
                        self.src_drag_start = event.position().toPoint()
                    else:
                        self.dst_drag_start = event.position().toPoint()
                    return True

            # 处理鼠标移动事件 (正常模式下的左键拖动和任何模式下的中键拖动)
            elif event.type() == QEvent.Type.MouseMove:
                if obj == self.ui.m_srcImgLabel and self.src_drag_start is not None:
                    # 计算拖动偏移量
                    delta = event.position().toPoint() - self.src_drag_start
                    self.src_offset += delta
                    self.src_drag_start = event.position().toPoint()
                    self.updateSrcImage()
                    return True
                elif obj == self.ui.m_dstImgLabel and self.dst_drag_start is not None:
                    # 计算拖动偏移量
                    delta = event.position().toPoint() - self.dst_drag_start
                    self.dst_offset += delta
                    self.dst_drag_start = event.position().toPoint()
                    self.updateDstImage()
                    return True

            # 处理鼠标释放事件 (正常模式下的左键拖动和任何模式下的中键拖动)
            elif event.type() == QEvent.Type.MouseButtonRelease:
                if (event.button() == Qt.MouseButton.LeftButton and self.mode == "normal") or event.button() == Qt.MouseButton.MiddleButton:
                    if obj == self.ui.m_srcImgLabel:
                        self.src_drag_start = None
                    else:
                        self.dst_drag_start = None
                    return True

        return super().eventFilter(obj, event)

    def updateSrcImage(self, isOrganize=False):
        current_item = self.ui.m_imgTreeWidget.currentItem()
        if not current_item or not current_item.parent() or current_item.parent().text(0) != "src":
            return

        img_name = current_item.text(0)
        src_img = self.srcImgs.get(img_name)
        if src_img is not None:
            # 获取标签大小
            label_size = self.ui.m_srcImgLabel.size()
            h, w = src_img.shape[:2]

            # 计算缩放比例，保持宽高比
            scale_w = label_size.width() / w
            scale_h = label_size.height() / h
            scale = min(scale_w, scale_h) * self.src_scale

            # 计算新的尺寸，保持宽高比
            new_w = int(w * scale)
            new_h = int(h * scale)

            # 缩放图像
            resized_img = cv2.resize(src_img, (new_w, new_h))
            rgb_img = cv2.cvtColor(resized_img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_img.shape
            qt_img = QImage(rgb_img.data, w, h, w * ch,
                            QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_img)

            # 创建空白图像，大小与标签相同
            result_pixmap = QPixmap(label_size)
            result_pixmap.fill(Qt.GlobalColor.transparent)

            # 在空白图像上绘制缩放后的图像，考虑偏移量
            painter = QPainter(result_pixmap)
            x = (label_size.width() - pixmap.width()) // 2 + self.src_offset.x()
            y = (label_size.height() - pixmap.height()
                 ) // 2 + self.src_offset.y()
            painter.drawPixmap(x, y, pixmap)

            # 绘制网格点
            if img_name in self.cornersPts and self.cornersPts[img_name]:
                # 设置红色画笔
                painter.setPen(Qt.GlobalColor.red)
                painter.setBrush(Qt.GlobalColor.red)

                for point in self.cornersPts[img_name]:
                    # 将原图坐标转换为显示坐标
                    display_x = int(point.x() * scale) + x
                    display_y = int(point.y() * scale) + y
                    # 绘制红色实心点
                    painter.drawEllipse(display_x - 5, display_y - 5, 10, 10)

                grid_dict = {}
                if isOrganize:
                    grid_dict = self.organizeGridPoints(
                        self.cornersPts[img_name])
                    self.grid_dict[img_name] = grid_dict
                else:
                    grid_dict = self.grid_dict[img_name]

                painter.setPen(Qt.GlobalColor.blue)
                painter.setBrush(Qt.GlobalColor.blue)
                # 绘制每个网格点及其序号
                for index, point in grid_dict.items():
                    # 将原图坐标转换为显示坐标
                    display_x = int(point.x() * scale) + x
                    display_y = int(point.y() * scale) + y
                    # 绘制红色实心点
                    painter.drawEllipse(display_x - 3, display_y - 3, 6, 6)
                    # 绘制序号
                    painter.setPen(Qt.GlobalColor.white)
                    painter.drawText(display_x + 6, display_y + 6, str(index))

            # 绘制套索线条
            if self.mode == "delete_grid_points" and len(self.lasso_points) > 1:
                # 设置黄色画笔
                painter.setPen(Qt.GlobalColor.yellow)

                # 绘制套索线条
                for i in range(len(self.lasso_points) - 1):
                    painter.drawLine(
                        self.lasso_points[i], self.lasso_points[i + 1])

                # 如果有超过2个点，连接最后一个点和第一个点
                if len(self.lasso_points) > 2:
                    painter.drawLine(
                        self.lasso_points[-1], self.lasso_points[0])

            painter.end()

            # 设置图像
            self.ui.m_srcImgLabel.setPixmap(result_pixmap)

    def updateDstImage(self):
        current_item = self.ui.m_imgTreeWidget.currentItem()
        if not current_item or not current_item.parent() or current_item.parent().text(0) != "src":
            return

        img_name = current_item.text(0)
        dst_img = self.dstImgs.get(img_name)
        if dst_img is not None:
            # 获取标签大小
            label_size = self.ui.m_dstImgLabel.size()
            h, w = dst_img.shape[:2]

            # 计算缩放比例，保持宽高比
            scale_w = label_size.width() / w
            scale_h = label_size.height() / h
            scale = min(scale_w, scale_h) * self.dst_scale

            # 计算新的尺寸，保持宽高比
            new_w = int(w * scale)
            new_h = int(h * scale)

            # 缩放图像
            resized_img = cv2.resize(dst_img, (new_w, new_h))
            rgb_img = cv2.cvtColor(resized_img, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_img.shape
            qt_img = QImage(rgb_img.data, w, h, w * ch,
                            QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_img)

            # 创建空白图像，大小与标签相同
            result_pixmap = QPixmap(label_size)
            result_pixmap.fill(Qt.GlobalColor.transparent)

            # 在空白图像上绘制缩放后的图像，考虑偏移量
            painter = QPainter(result_pixmap)
            x = (label_size.width() - pixmap.width()) // 2 + self.dst_offset.x()
            y = (label_size.height() - pixmap.height()
                 ) // 2 + self.dst_offset.y()
            painter.drawPixmap(x, y, pixmap)

            # # 将无序点转换为有序网格结构
            # grid_dict = self.organizeGridPoints(self.cornersPts[img_name])
            # painter.setPen(Qt.GlobalColor.blue)
            # painter.setBrush(Qt.GlobalColor.blue)
            # # 绘制每个网格点及其序号
            # for index, point in grid_dict.items():
            #     # 将原图坐标转换为显示坐标
            #     display_x = int(point.x() * scale) + x
            #     display_y = int(point.y() * scale) + y
            #     # 绘制红色实心点
            #     painter.drawEllipse(display_x - 3, display_y - 3, 6, 6)
            #     # 绘制序号
            #     painter.setPen(Qt.GlobalColor.white)
            #     painter.drawText(display_x + 6, display_y + 6, str(index))

            # 绘制网格点
            # if img_name in self.cornersPts2 and self.cornersPts2[img_name]:
            #     # 设置红色画笔
            #     painter.setPen(Qt.GlobalColor.red)
            #     painter.setBrush(Qt.GlobalColor.red)

            #     # 绘制每个网格点
            #     for point in self.cornersPts2[img_name]:
            #         # 将原图坐标转换为显示坐标
            #         display_x = int(point.x() * scale) + x
            #         display_y = int(point.y() * scale) + y
            #         # 绘制红色实心点
            #         painter.drawEllipse(display_x - 3, display_y - 3, 6, 6)

            painter.end()

            # 设置图像
            self.ui.m_dstImgLabel.setPixmap(result_pixmap)

    def organizeGridPoints(self, cornersPts):
        """
        参数:
        cornersPts -- 包含网格点坐标的列表，每个点是QPoint(x, y)对象
        返回:
        包含列行索引的字典，键为(列,行)字符串，值为QPoint对象
        处理网格中缺失点的情况，保持其他点的列行索引不变
        """
        # 处理空列表情况
        if not cornersPts:
            return {}

        # 设置阈值参数
        x_thread = 150  # 同一列的x坐标误差阈值
        y_thread = 100  # 同一行的y坐标误差阈值

        # 提取坐标到numpy数组
        points = np.array([[p.x(), p.y()] for p in cornersPts])

        # 按x坐标排序（从小到大）
        sorted_indices = np.argsort(points[:, 0])
        sorted_points = points[sorted_indices]

        # 按x坐标聚类形成列
        cols = []
        if len(sorted_points) > 0:  # 确保有点可处理
            current_col = [sorted_indices[0]]
            current_x = sorted_points[0, 0]

            for i in range(1, len(sorted_points)):
                if abs(sorted_points[i, 0] - current_x) <= x_thread:
                    # 同一列
                    current_col.append(sorted_indices[i])
                else:
                    # 新的一列
                    cols.append(current_col)
                    current_col = [sorted_indices[i]]
                    current_x = sorted_points[i, 0]

            # 添加最后一列
            if current_col:
                cols.append(current_col)

        # 对每一列内的点按y坐标排序
        for i in range(len(cols)):
            col_points = points[cols[i]]
            y_sorted_indices = np.argsort(col_points[:, 1])
            cols[i] = [cols[i][j] for j in y_sorted_indices]

        # 确定网格的行数（取最长列的长度）
        if not cols:
            return {}

        # 找出所有列中的最大y坐标和最小y坐标，用于确定行的位置
        all_y_coords = [points[idx, 1] for col in cols for idx in col]
        min_y, max_y = min(all_y_coords), max(all_y_coords)

        # 估计行间距
        max_col_len = max(len(col) for col in cols)
        if max_col_len <= 1:
            row_spacing = 1  # 如果每列最多只有一个点，设置默认间距
        else:
            row_spacing = (max_y - min_y) / (max_col_len - 1)

        # 如果行间距太小，设置一个最小值
        row_spacing = max(row_spacing, 10)  # 确保行间距至少为10像素

        # 构建网格字典，处理缺失点和重复键
        grid_dict = {}
        for col_idx, col in enumerate(cols):
            col_points = points[col]

            # 对于每一列，根据y坐标确定行索引
            for point_idx in col:
                y_coord = points[point_idx, 1]
                # 计算行索引：根据点的y坐标与最小y坐标的差值，除以行间距得到
                row_idx = round((y_coord - min_y) / row_spacing)

                # 将点添加到网格字典中，使用列行索引作为键
                key = f"{row_idx},{col_idx}"

                # 如果键已存在，生成带负号的新键
                if key in grid_dict:
                    # 寻找可用的负数键
                    negative_row = -1
                    while f"{negative_row},{col_idx}" in grid_dict:
                        negative_row -= 1
                    key = f"{negative_row},{col_idx}"

                grid_dict[key] = cornersPts[point_idx]

        return grid_dict

    def load_grid_dict(self):
        grid_dict_folder = os.path.join(self.m_folderPath, 'gridDict')
        if os.path.exists(grid_dict_folder):
            for file_name in os.listdir(grid_dict_folder):
                if file_name.endswith('_grid_dict.txt'):
                    # 获取基础文件名（不含扩展名）
                    base_name = file_name.replace('_grid_dict.txt', '')
                    # 查找对应的图片文件
                    img_name = None
                    for img_file in self.srcImgs.keys():
                        if os.path.splitext(img_file)[0] == base_name:
                            img_name = img_file
                            break

                    if img_name:
                        self.grid_dict[img_name] = {}
                        with open(os.path.join(grid_dict_folder, file_name), 'r') as f:
                            for line in f:
                                parts = line.strip().split(',')
                                if len(parts) == 4:
                                    row_idx, col_idx, x, y = parts
                                    key = f"{row_idx},{col_idx}"
                                    self.grid_dict[img_name][key] = QPoint(
                                        int(x), int(y))

    def manualGridPointsIndex(self):
        """使用Qt文本控件为每个点分配编号，支持手动编辑网格点的索引"""
        # 获取当前选中的图片
        current_item = self.ui.m_imgTreeWidget.currentItem()
        if not current_item or not current_item.parent() or current_item.parent().text(0) != "src":
            self.statusBar().showMessage("请先选择一张图片")
            return

        img_name = current_item.text(0)
        if img_name not in self.srcImgs:
            self.statusBar().showMessage("图片不存在")
            return

        # 获取图像和点
        img = self.srcImgs[img_name]
        points = self.cornersPts.get(img_name, [])

        if not points:
            self.statusBar().showMessage("当前图片没有网格点")
            return

        # 如果已有grid_dict，使用它；否则生成新的
        grid_dict = {}
        if img_name in self.grid_dict and self.grid_dict[img_name]:
            grid_dict = self.grid_dict[img_name]
        else:
            grid_dict = self.organizeGridPoints(points)

        # 清除可能存在的旧文本控件
        for child in self.ui.m_srcImgLabel.children():
            child.deleteLater()

        # 设置模式为手动编号模式
        self.mode = "manual_grid_index"
        self.statusBar().showMessage("手动编号模式：点击文本框修改网格点编号，完成后点击'完成'按钮保存")

        # 获取标签大小和图像信息
        label_size = self.ui.m_srcImgLabel.size()
        h, w = img.shape[:2]

        # 计算缩放比例，保持宽高比
        scale_w = label_size.width() / w
        scale_h = label_size.height() / h
        scale = min(scale_w, scale_h) * self.src_scale

        # 计算图像在标签中的位置
        x = (label_size.width() - w * scale) // 2 + self.src_offset.x()
        y = (label_size.height() - h * scale) // 2 + self.src_offset.y()

        # 创建文本控件字典，用于后续保存
        self.grid_text_edits = {}

        # 为每个网格点创建文本控件
        for index, point in grid_dict.items():
            # 将原图坐标转换为显示坐标
            display_x = int(point.x() * scale) + x
            display_y = int(point.y() * scale) + y

            # 创建文本控件
            text_edit = QLineEdit(self.ui.m_srcImgLabel)
            text_edit.setText(str(index))
            text_edit.setGeometry(int(display_x + 6),
                                  int(display_y - 10), 30, 20)  # 位置和大小
            text_edit.setStyleSheet(
                "background-color: rgba(255, 255, 255, 150); color: black;")
            text_edit.show()

            # 存储文本控件和对应的点
            self.grid_text_edits[point] = text_edit

        # 提示用户如何操作
        self.statusBar().showMessage("手动编号模式：点击文本框修改网格点编号，完成后点击'完成'按钮保存")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
