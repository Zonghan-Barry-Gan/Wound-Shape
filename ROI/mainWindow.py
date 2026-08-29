from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog, QTreeWidgetItem
from PyQt6.QtCore import QDir, Qt, QEvent, QPoint
from PyQt6.QtGui import QImage, QPixmap, QPainter, QTransform
from generationFile.mainWindow_ui import Ui_MainWindow
import cv2
import sys
import os
import numpy as np
import json


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        # 参数
        self.cellSize = 300                      # 畸变矫正展开时设置的cellSize
        self.dis_per_pixel = 8.0 / self.cellSize  # 每像素距离   单位：mm/pixel

        # 成员变量
        self.m_folderPath = "./data"

        self.srcImgs = {}  # key: imgName, value: img
        self.dstImgs = {}  # key: imgName, value: img
        self.roiPts = {}   # key: imgName, value: {roi_index: [points]}

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

    def initUI(self):
        # 设置窗口属性
        self.setWindowTitle("ROI标注工具")
        # self.setFixedSize(1080, 720)
        self.ui.m_imgTreeWidget.setHeaderLabels(["文件名"])
        self.ui.m_imgTreeWidget.header().setDefaultAlignment(
            Qt.AlignmentFlag.AlignCenter)                      # 设置表头居中
        self.ui.m_imgTreeWidget.setAlternatingRowColors(True)  # 设置交替行颜色
        self.ui.m_imgTreeWidget.expandAll()  # 默认展开所有项

        # # 设置图像标签可以接收键盘焦点
        self.ui.m_srcImgLabel.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.ui.m_dstImgLabel.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # 设置自动对比度复选框
        self.ui.m_autoContrastCheck.setText("自动对比度增强")
        self.ui.m_autoContrastCheck.setChecked(True)  # 默认开启
        self.ui.m_contrastAlphaHSlider.setEnabled(False)

        # 信号与槽
        self.ui.m_openFolderAction.triggered.connect(self.openFolder)
        self.ui.m_imgTreeWidget.itemClicked.connect(self.onTreeItemClicked)
        self.ui.m_getGridCornersBtn.clicked.connect(
            self.startGetGridPoints)  # 获取点按钮
        self.ui.m_deleteGridCornersBtn.clicked.connect(
            self.startDeleteGridPoints)  # 删除点按钮
        self.ui.m_finishGridCornersBtn.clicked.connect(
            self.finishGridPoints)  # 完成按钮
        self.ui.m_saveImgBtn.clicked.connect(self.saveGridPoints)
        self.ui.m_roiIndexCBox.currentIndexChanged.connect(
            self.onRoiIndexChanged)
        # 添加自动对比度复选框状态变化信号连接
        self.ui.m_autoContrastCheck.stateChanged.connect(
            self.onContrastCheckChanged)
        # 添加对比度滑块值变化信号连接
        self.ui.m_contrastAlphaHSlider.valueChanged.connect(
            self.onContrastSliderChanged)

        # 为图像标签安装事件过滤器
        self.ui.m_srcImgLabel.installEventFilter(self)
        self.ui.m_dstImgLabel.installEventFilter(self)

    def onTreeItemClicked(self, item, column):
        # 检查是否点击的是src文件夹下的图片项
        parent = item.parent()
        if parent is None or parent.text(0) != "src":
            return

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

        # 确保当前图片在roiPts中有记录
        img_name = item.text(0)
        if img_name not in self.roiPts:
            self.roiPts[img_name] = {}

        # 使用updateSrcImage和updateDstImage方法来显示图像和网格点
        self.updateSrcImage()
        self.updateDstImage()

    def openFolder(self):
        folder = self.m_folderPath
        if folder:
            self.loadImages(folder)

    def loadImages(self, folder_path):
        self.ui.m_imgTreeWidget.clear()
        self.srcImgs.clear()
        self.dstImgs.clear()
        self.roiPts.clear()

        image_exts = ('.jpg', '.JPG', '.jpeg', '.png', '.bmp', '.gif')
        src_folder = os.path.join(folder_path, 'src')
        dst_folder = os.path.join(folder_path, 'dst')
        roi_points_folder = os.path.join(folder_path, 'roi_points')

        # 创建roi_points文件夹（如果不存在）
        if not os.path.exists(roi_points_folder):
            os.makedirs(roi_points_folder)

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
                    # 旋转图像后重新赋值给img变量
                    rotated_img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
                    if rotated_img is not None:
                        self.srcImgs[file_name] = rotated_img

                        item = QTreeWidgetItem(src_item)
                        item.setText(0, file_name)

                        # 为每张图片初始化空的ROI点字典
                        self.roiPts[file_name] = {}

                        # 尝试加载ROI点数据
                        img_name_without_ext = os.path.splitext(file_name)[0]
                        for roi_index in range(1, 5):  # ROI_1 到 ROI_4
                            roi_file_name = f"{img_name_without_ext}_roi_{roi_index}.txt"
                            roi_file_path = os.path.join(
                                roi_points_folder, roi_file_name)
                            if os.path.exists(roi_file_path):
                                points = []
                                with open(roi_file_path, 'r') as f:
                                    for line in f:
                                        if line.strip():  # 跳过空行
                                            x, y = map(
                                                int, line.strip().split(','))
                                            points.append(QPoint(x, y))
                                self.roiPts[file_name][roi_index] = points

        self.dstImgs = self.srcImgs.copy()  # 使用src的图片初始化

    # 开始获取网格点模式

    def startGetGridPoints(self):
        self.mode = "get_grid_points"
        self.statusBar().showMessage("获取椭圆点模式：点击图像添加椭圆点")

    # 开始删除网格点模式
    def startDeleteGridPoints(self):
        self.mode = "delete_grid_points"
        self.lasso_points = []
        self.statusBar().showMessage("删除椭圆点模式：拖动鼠标画套索删除椭圆点")

    # 完成网格点操作
    def finishGridPoints(self):
        self.mode = "normal"
        self.lasso_points = []
        self.statusBar().showMessage("正常模式")

    # ROI索引切换事件处理
    def onRoiIndexChanged(self, index):
        self.updateSrcImage()
        self.updateDstImage()

    # 自动对比度
    def onContrastCheckChanged(self, state):
        self.updateSrcImage()
        self.updateDstImage()
        print(state)
        if state == 2:
            self.ui.m_contrastAlphaHSlider.setEnabled(False)
        else:
            self.ui.m_contrastAlphaHSlider.setEnabled(True)

    # 对比度滑块值变化

    def onContrastSliderChanged(self, value):
        # 更新源图像和目标图像显示
        self.updateSrcImage()
        self.updateDstImage()

    # 保存网格点数据
    def saveGridPoints(self):
        # 创建保存文件夹
        roi_points_folder = os.path.join(self.m_folderPath, 'roi_points')
        if not os.path.exists(roi_points_folder):
            os.makedirs(roi_points_folder)

        dst_folder = os.path.join(self.m_folderPath, 'dst')
        if not os.path.exists(dst_folder):
            os.makedirs(dst_folder)
        # 保存所有图像的所有ROI索引数据
        saved_count = 0
        saved_roi_images = 0

        # 用于收集所有ROI的物理面积数据
        roi_areas_data = []

        for img_name in self.srcImgs.keys():
            display_img = self.dstImgs.get(img_name).copy()
            if display_img is not None:
                if self.ui.m_autoContrastCheck.isChecked():  # 自动对比度增强处理
                    if len(display_img.shape) == 3:
                        b, g, r = cv2.split(display_img)
                        # 创建CLAHE对象
                        clahe = cv2.createCLAHE(
                            clipLimit=2.0, tileGridSize=(8, 8))
                        # 对每个通道应用CLAHE
                        b_clahe = clahe.apply(b)
                        g_clahe = clahe.apply(g)
                        r_clahe = clahe.apply(r)
                        display_img = cv2.merge([b_clahe, g_clahe, r_clahe])
                    else:
                        clahe = cv2.createCLAHE(
                            clipLimit=2.0, tileGridSize=(8, 8))
                        display_img = clahe.apply(display_img)
                else:
                    alpha = self.ui.m_contrastAlphaHSlider.value() / 10  # 对比度增强系数
                    beta = 0     # 亮度调整值
                    display_img = cv2.convertScaleAbs(
                        display_img, alpha=alpha, beta=beta)

            colors = [(0, 0, 255), (0, 255, 0), (255, 0, 0), (255, 0, 255)]
            if img_name in self.roiPts:
                for roi_index in range(1, 5):  # ROI_1 到 ROI_4
                    if roi_index in self.roiPts[img_name]:
                        # 保存点数据并获取物理面积
                        area_mm2 = self.save_single_image_points(
                            img_name, roi_points_folder, roi_index)
                        saved_count += 1

                        # 如果有足够的点可以拟合椭圆，则认为保存了ROI图像
                        if len(self.roiPts[img_name][roi_index]) >= 5:
                            saved_roi_images += 1
                            points = self.roiPts[img_name][roi_index]
                            np_points = np.array(
                                [[p.x(), p.y()] for p in points], dtype=np.float32)
                            # 拟合椭圆
                            ellipse = cv2.fitEllipse(np_points)
                            cv2.ellipse(display_img, ellipse,
                                        colors[roi_index-1], 2)

                            # 如果成功计算了物理面积，添加到数据列表
                            if area_mm2 is not None:
                                img_name_without_ext = os.path.splitext(img_name)[
                                    0]
                                roi_areas_data.append({
                                    'img_name': img_name_without_ext,
                                    'roi_index': roi_index,
                                    'area_mm2': area_mm2
                                })
            dst_image_path = os.path.join(dst_folder, img_name)
            cv2.imwrite(dst_image_path, display_img)

        # 生成CSV文件
        if roi_areas_data:
            self.generate_roi_areas_csv(roi_areas_data)
            csv_info = f"并生成了ROI面积CSV文件"
        else:
            csv_info = ""

        if saved_count > 0:
            if saved_roi_images > 0:
                self.statusBar().showMessage(
                    f"已保存 {saved_count} 个ROI点数据文件和 {saved_roi_images} 个ROI图像{csv_info}")
            else:
                self.statusBar().showMessage(f"已保存 {saved_count} 个ROI点数据文件")
        else:
            self.statusBar().showMessage("没有ROI点数据需要保存")

    # 生成ROI面积CSV文件
    def generate_roi_areas_csv(self, roi_areas_data):
        """生成包含所有ROI物理面积数据的CSV文件

        Args:
            roi_areas_data: 包含ROI面积数据的列表，每个元素是一个字典，包含img_name, roi_index和area_mm2
        """
        try:
            # 创建保存ROI图像的文件夹
            roi_images_folder = os.path.join(self.m_folderPath, 'roi_images')
            if not os.path.exists(roi_images_folder):
                os.makedirs(roi_images_folder)

            # 生成CSV文件路径
            csv_path = os.path.join(roi_images_folder, 'roi_areas.csv')

            # 写入CSV文件
            with open(csv_path, 'w', newline='') as csvfile:
                # 写入标题行
                csvfile.write("img_name,roi_index,area_mm2\n")

                # 写入数据行
                for data in roi_areas_data:
                    csvfile.write(
                        f"{data['img_name']},{data['roi_index']},{data['area_mm2']}\n")

            print(f"已生成ROI面积CSV文件: {csv_path}")
            return csv_path
        except Exception as e:
            print(f"生成ROI面积CSV文件失败: {e}")
            return None

    # 保存单张图片的ROI点
    def save_single_image_points(self, img_name, roi_points_folder, roi_index):
        img_name_without_ext = os.path.splitext(img_name)[0]
        file_path = os.path.join(
            roi_points_folder, f"{img_name_without_ext}_roi_{roi_index}.txt")

        # 即使没有ROI点，也创建空文件
        with open(file_path, 'w') as f:
            if img_name in self.roiPts and roi_index in self.roiPts[img_name] and self.roiPts[img_name][roi_index]:
                for point in self.roiPts[img_name][roi_index]:
                    f.write(f"{point.x()},{point.y()}\n")

        # 如果有足够的点，拟合椭圆并保存ROI图像
        area_mm2 = None
        if img_name in self.roiPts and roi_index in self.roiPts[img_name] and len(self.roiPts[img_name][roi_index]) >= 5:
            try:
                # 获取原图
                src_img = self.srcImgs.get(img_name)
                if src_img is None:
                    return None

                # 提取并保存ROI图像，获取物理面积
                roi_image_path, area_mm2 = self.extract_and_save_roi_image(
                    img_name, roi_index, margin=0)

            except Exception as e:
                print(f"保存ROI图像失败: {e}")
                return None

        # # 如果是当前选中的图片，更新状态栏
        # current_item = self.ui.m_imgTreeWidget.currentItem()
        # if current_item and current_item.text(0) == img_name:
        #     if img_name in self.roiPts and roi_index in self.roiPts[img_name] and self.roiPts[img_name][roi_index]:
        #         points_count = len(self.roiPts[img_name][roi_index])
        #         if points_count >= 5:
        #             area_info = f"，物理面积: {area_mm2} mm²" if area_mm2 is not None else ""
        #             self.statusBar().showMessage(
        #                 f"已保存 {points_count} 个椭圆点到 {file_path} 并保存ROI图像{area_info}")
        #         else:
        #             self.statusBar().showMessage(
        #                 f"已保存 {points_count} 个椭圆点到 {file_path}")
        #     else:
        #         self.statusBar().showMessage(f"已创建空的椭圆点文件 {file_path}")

        return area_mm2

    # 提取并保存ROI图像
    def extract_and_save_roi_image(self, img_name, roi_index, margin=0):
        """根据椭圆点提取ROI图像并保存

        Args:
            img_name: 图像名称
            roi_index: ROI索引
            margin: 边缘留白像素数，默认为10

        Returns:
            tuple: (保存的ROI图像路径, 椭圆物理面积(mm²))，如果保存失败则返回(None, None)
        """
        try:
            # 获取原图
            src_img = self.srcImgs.get(img_name)
            if src_img is None:
                return None, None

            # 转换点为numpy数组
            points = self.roiPts[img_name][roi_index]
            np_points = np.array([[p.x(), p.y()]
                                  for p in points], dtype=np.float32)

            # 拟合椭圆
            ellipse = cv2.fitEllipse(np_points)
            center = (int(ellipse[0][0]), int(ellipse[0][1]))
            axes = (int(ellipse[1][0] / 2), int(ellipse[1][1] / 2))
            angle = ellipse[2]

            # 计算椭圆面积（像素）
            # 椭圆面积 = π × a × b，其中a和b是椭圆的半长轴和半短轴
            area_px = np.pi * (ellipse[1][0] / 2) * (ellipse[1][1] / 2)
            area_px_int = int(area_px)

            # 计算椭圆的实际物理面积（mm²）
            # 面积转换：像素面积 × (mm/pixel)²
            area_mm2 = area_px * (self.dis_per_pixel ** 2)
            area_mm2_rounded = round(area_mm2, 2)  # 保留两位小数

            # 计算椭圆的包围框
            # 计算椭圆的包围框
            box_width = int(ellipse[1][0])
            box_height = int(ellipse[1][1])

            # 如果包围框尺寸小于cellSize，则扩展到cellSize
            target_size = self.cellSize + 60
            if box_width < target_size:
                delta = target_size - box_width
                box_width = target_size
                x1 = max(0, center[0] - target_size//2 - delta//2)
                x2 = min(src_img.shape[1], center[0] +
                         target_size//2 + delta//2)
            else:
                x1 = max(0, center[0] - box_width//2)
                x2 = min(src_img.shape[1], center[0] + box_width//2)

            if box_height < target_size:
                delta = target_size - box_height
                box_height = target_size
                y1 = max(0, center[1] - target_size//2 - delta//2)
                y2 = min(src_img.shape[0], center[1] +
                         target_size//2 + delta//2)
            else:
                y1 = max(0, center[1] - box_height//2)
                y2 = min(src_img.shape[0], center[1] + box_height//2)

            # 最终确保ROI尺寸为cellSize x cellSize
            x1 = max(0, center[0] - target_size//2)
            y1 = max(0, center[1] - target_size//2)
            x2 = x1 + target_size
            y2 = y1 + target_size

            # 二次边界检查
            x2 = min(x2, src_img.shape[1])
            y2 = min(y2, src_img.shape[0])
            x1 = x2 - target_size if x2 == src_img.shape[1] else x1
            y1 = y2 - target_size if y2 == src_img.shape[0] else y1

            # 截取ROI区域
            roi_img = src_img[y1:y2, x1:x2].copy()

            # 如果尺寸不满足，要求打印尺寸出来
            if roi_img.shape[0] != target_size or roi_img.shape[1] != target_size:
                print(f"ROI尺寸不满足要求：{roi_img.shape}")

            # 创建保存ROI图像的文件夹
            roi_images_folder = os.path.join(
                self.m_folderPath, 'roi_images')
            if not os.path.exists(roi_images_folder):
                os.makedirs(roi_images_folder)

            # 保存ROI图像，文件名中包含面积信息
            img_name_without_ext = os.path.splitext(img_name)[0]
            roi_image_path = os.path.join(
                roi_images_folder, f"{img_name_without_ext}-roi{roi_index}.png")
            cv2.imwrite(roi_image_path, roi_img)

            # # 保存ellipse 信息
            # ellipse_info_path = os.path.join(
            #     roi_images_folder, f"{img_name_without_ext}-roi{roi_index}-ellipse.txt")
            # with open(ellipse_info_path, 'w') as f:
            #     f.write(
            #         f"{center[0]},{center[1]},{axes[0]},{axes[1]},{angle}\n")

            # 保存ellipse 信息 使用json
            print(f"{center[0]},{center[1]},{axes[0]},{axes[1]},{angle}\n")
            ellipse_info_dir = os.path.join(
                self.m_folderPath, 'ellipse_info')
            if not os.path.exists(ellipse_info_dir):
                os.makedirs(ellipse_info_dir)

            ellipse_info_path = os.path.join(
                ellipse_info_dir, f"{img_name_without_ext}-roi{roi_index}-ellipse.json")
            with open(ellipse_info_path, 'w') as f:
                ellipse_info = {
                    "type": "ellipse",
                    "img_name": img_name_without_ext,
                    "index": roi_index,
                    "center":  (ellipse[0][0], ellipse[0][1]),
                    "axes": (ellipse[1][0] / 2, ellipse[1][1] / 2),
                    "angle": ellipse[2],
                    "np_points": np_points.tolist(),
                }
                json.dump(ellipse_info, f)
            return roi_image_path, area_mm2_rounded

        except Exception as e:
            print(f"提取并保存ROI图像失败: {e}")
            return None, None

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
            # 处理Tab键事件，用于切换ROI索引
            if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Tab:
                # 获取当前ROI索引
                current_index = self.ui.m_roiIndexCBox.currentIndex()
                # 计算新的索引（0-3循环）
                new_index = (current_index + 1) % 4
                # 设置新的索引
                self.ui.m_roiIndexCBox.setCurrentIndex(new_index)
                # 返回True表示事件已处理
                return True

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

                        # 获取当前选择的ROI索引
                        roi_index_text = self.ui.m_roiIndexCBox.currentText()
                        roi_index = int(roi_index_text.split('_')[1])

                        # 初始化roiPts字典
                        if img_name not in self.roiPts:
                            self.roiPts[img_name] = {}
                        if roi_index not in self.roiPts[img_name]:
                            self.roiPts[img_name][roi_index] = []

                        # 添加ROI点
                        self.roiPts[img_name][roi_index].append(original_pos)
                        self.statusBar().showMessage(
                            f"添加椭圆点: ({original_pos.x()}, {original_pos.y()}) 到 ROI_{roi_index}")

                        # 更新图像显示
                        self.updateSrcImage()
                        self.updateDstImage()

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
                        self.updateDstImage()
                        return True

                    elif event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton and self.lasso_points:
                        # 获取当前选择的ROI索引
                        roi_index_text = self.ui.m_roiIndexCBox.currentText()
                        roi_index = int(roi_index_text.split('_')[1])

                        # 完成套索绘制，删除套索内的点
                        if img_name in self.roiPts and roi_index in self.roiPts[img_name] and len(self.roiPts[img_name][roi_index]) > 0:
                            # 获取标签大小和图像信息
                            label_size = self.ui.m_srcImgLabel.size()

                            # 转换套索点为原图坐标系中的多边形
                            lasso_polygon = []
                            for point in self.lasso_points:
                                lasso_polygon.append(self.display_to_original_coords(
                                    point, label_size, src_img.shape, self.src_scale, self.src_offset))

                            # 找出在套索内的点
                            points_to_remove = []
                            for i, point in enumerate(self.roiPts[img_name][roi_index]):
                                if self.point_in_polygon(point, lasso_polygon):
                                    points_to_remove.append(i)

                            # 从后往前删除点，避免索引变化
                            for i in sorted(points_to_remove, reverse=True):
                                del self.roiPts[img_name][roi_index][i]

                            self.statusBar().showMessage(
                                f"删除了 {len(points_to_remove)} 个椭圆点")

                        # 清空套索点
                        self.lasso_points = []
                        # 更新图像显示
                        self.updateSrcImage()
                        self.updateDstImage()
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

            # 处理鼠标按下事件 (正常模式下的拖动)
            elif event.type() == QEvent.Type.MouseButtonPress and self.mode == "normal":
                if event.button() == Qt.MouseButton.LeftButton:
                    if obj == self.ui.m_srcImgLabel:
                        self.src_drag_start = event.position().toPoint()
                    else:
                        self.dst_drag_start = event.position().toPoint()
                    return True

            # 处理鼠标移动事件 (正常模式下的拖动)
            elif event.type() == QEvent.Type.MouseMove and self.mode == "normal":
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

            # 处理鼠标释放事件 (正常模式下的拖动)
            elif event.type() == QEvent.Type.MouseButtonRelease and self.mode == "normal":
                if event.button() == Qt.MouseButton.LeftButton:
                    if obj == self.ui.m_srcImgLabel:
                        self.src_drag_start = None
                    else:
                        self.dst_drag_start = None
                    return True

        return super().eventFilter(obj, event)

    def updateSrcImage(self):
        current_item = self.ui.m_imgTreeWidget.currentItem()
        if not current_item or not current_item.parent() or current_item.parent().text(0) != "src":
            return

        img_name = current_item.text(0)
        src_img = self.srcImgs.get(img_name).copy()
        if src_img is not None:
            if self.ui.m_autoContrastCheck.isChecked():  # 自动对比度增强处理
                if len(src_img.shape) == 3:
                    b, g, r = cv2.split(src_img)
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                    # 对每个通道应用CLAHE
                    b_clahe = clahe.apply(b)
                    g_clahe = clahe.apply(g)
                    r_clahe = clahe.apply(r)
                    src_img = cv2.merge([b_clahe, g_clahe, r_clahe])
                else:
                    # 灰度图像直接应用CLAHE
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                    src_img = clahe.apply(src_img)

            else:
                alpha = self.ui.m_contrastAlphaHSlider.value() / 10  # 对比度增强系数
                beta = 0     # 亮度调整值
                src_img = cv2.convertScaleAbs(src_img, alpha=alpha, beta=beta)

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

            # 获取当前选择的ROI索引
            roi_index_text = self.ui.m_roiIndexCBox.currentText()
            roi_index = int(roi_index_text.split('_')[1])

            # 根据当前 roi index 绘制点
            if img_name in self.roiPts and roi_index in self.roiPts[img_name] and self.roiPts[img_name][roi_index]:
                # 设置红色画笔
                painter.setPen(Qt.GlobalColor.red)
                painter.setBrush(Qt.GlobalColor.red)

                for point in self.roiPts[img_name][roi_index]:
                    # 将原图坐标转换为显示坐标
                    display_x = int(point.x() * scale) + x
                    display_y = int(point.y() * scale) + y
                    # 绘制红色实心点
                    painter.drawEllipse(display_x - 4, display_y - 4, 8, 8)

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
        dst_img = self.dstImgs.get(img_name).copy()
        if dst_img is not None:
            if self.ui.m_autoContrastCheck.isChecked():  # 自动对比度增强处理
                if len(dst_img.shape) == 3:
                    b, g, r = cv2.split(dst_img)
                    # 创建CLAHE对象
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                    # 对每个通道应用CLAHE
                    b_clahe = clahe.apply(b)
                    g_clahe = clahe.apply(g)
                    r_clahe = clahe.apply(r)
                    dst_img = cv2.merge([b_clahe, g_clahe, r_clahe])
                else:
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                    dst_img = clahe.apply(dst_img)
            else:
                alpha = self.ui.m_contrastAlphaHSlider.value() / 10  # 对比度增强系数
                beta = 0     # 亮度调整值
                dst_img = cv2.convertScaleAbs(dst_img, alpha=alpha, beta=beta)

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

            # 绘制所有ROI索引的点
            if img_name in self.roiPts:
                # 不同ROI索引使用不同颜色
                colors = [
                    Qt.GlobalColor.red,     # ROI_1
                    Qt.GlobalColor.green,   # ROI_2
                    Qt.GlobalColor.blue,    # ROI_3
                    Qt.GlobalColor.magenta  # ROI_4
                ]

                for roi_index in range(1, 5):  # ROI_1 到 ROI_4
                    if roi_index in self.roiPts[img_name] and self.roiPts[img_name][roi_index]:
                        # 设置对应颜色
                        color = colors[roi_index - 1]
                        painter.setPen(color)
                        painter.setBrush(color)

                        # 绘制点
                        points = self.roiPts[img_name][roi_index]
                        for point in points:
                            # 将原图坐标转换为显示坐标
                            display_x = int(point.x() * scale) + x
                            display_y = int(point.y() * scale) + y
                            # 绘制实心点
                            painter.drawEllipse(
                                display_x - 4, display_y - 4, 8, 8)

                            # 显示ROI索引编号
                            painter.drawText(
                                display_x + 5, display_y + 5, str(roi_index))

                        # 如果点数足够，拟合椭圆
                        if len(points) >= 5:  # 拟合椭圆至少需要5个点
                            try:
                                # 转换点为numpy数组
                                np_points = np.array(
                                    [[p.x(), p.y()] for p in points], dtype=np.float32)
                                # 拟合椭圆
                                ellipse = cv2.fitEllipse(np_points)
                                # 绘制椭圆
                                center = (
                                    int(ellipse[0][0] * scale) + x, int(ellipse[0][1] * scale) + y)
                                axes = (
                                    int(ellipse[1][0] * scale / 2), int(ellipse[1][1] * scale / 2))
                                angle = ellipse[2]
                                painter.setPen(color)
                                painter.setBrush(Qt.BrushStyle.NoBrush)  # 不填充

                                # 计算椭圆面积
                                # 椭圆面积 = π × a × b，其中a和b是椭圆的半长轴和半短轴
                                # 注意这里使用原始椭圆的轴长（未缩放）来计算实际面积
                                area = np.pi * \
                                    (ellipse[1][0] / 2) * (ellipse[1][1] / 2)
                                area_text = f"{int(area)}"

                                # 保存当前画布状态
                                painter.save()
                                # 移动到椭圆中心
                                painter.translate(center[0], center[1])
                                # 旋转画布
                                painter.rotate(angle)
                                # 绘制椭圆（中心点在原点）
                                painter.drawEllipse(-axes[0], -
                                                    axes[1], axes[0] * 2, axes[1] * 2)
                                # 恢复画布状态
                                painter.restore()

                                # 设置文本颜色和字体
                                painter.setPen(color)
                                font = painter.font()
                                font.setBold(True)
                                painter.setFont(font)

                                # 绘制面积文本在椭圆中心
                                # 计算文本宽度以便居中显示
                                text_rect = painter.fontMetrics().boundingRect(area_text)
                                text_x = center[0] - text_rect.width() // 2
                                text_y = center[1] + text_rect.height() // 2
                                painter.drawText(text_x, text_y, area_text)
                            except Exception as e:
                                print(f"拟合椭圆失败: {e}")

            painter.end()

            # 设置图像
            self.ui.m_dstImgLabel.setPixmap(result_pixmap)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
