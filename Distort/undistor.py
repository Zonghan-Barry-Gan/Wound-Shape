from math import fabs
import cv2
import os
import numpy as np


class Undistorter:
    def __init__(self, data_folder='data'):
        self.data_folder = data_folder
        self.srcImgs = {}
        self.grid_dict = {}
        self.dst_grid_dict = {}
        self.cell_size = 300  # 网格大小 像素
        self.load_images()
        self.load_grid_dict()
        self.validate_image_grid_mapping()

    def load_images(self):
        src_folder = os.path.join(self.data_folder, 'src')
        if os.path.exists(src_folder):
            for filename in os.listdir(src_folder):
                if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
                    img_path = os.path.join(src_folder, filename)
                    self.srcImgs[filename] = cv2.imread(img_path)

    def load_grid_dict(self):
        grid_folder = os.path.join(self.data_folder, 'gridDict')
        if not os.path.exists(grid_folder):
            return

        for filename in os.listdir(grid_folder):
            if filename.endswith('_grid_dict.txt'):
                # 匹配原始图像名称并保留原扩展名
                base_part = filename.replace('_grid_dict.txt', '')
                matching_imgs = [
                    name for name in self.srcImgs if name.startswith(base_part)]
                if not matching_imgs:
                    continue
                img_name = matching_imgs[0]

                if img_name not in self.srcImgs:
                    continue

                self.grid_dict[img_name] = {}
                try:
                    with open(os.path.join(grid_folder, filename), 'r') as f:
                        for line in f:
                            parts = line.strip().split(',')
                            if len(parts) != 4:
                                continue
                            row, col, x, y = map(int, parts)
                            self.grid_dict[img_name][f"{row},{col}"] = (x, y)
                except Exception as e:
                    print(f"Error loading {filename}: {str(e)}")

    def validate_image_grid_mapping(self):
        """验证图片与网格数据的映射关系"""
        image_keys = set(self.srcImgs.keys())
        grid_keys = set(self.grid_dict.keys())

        missing_images = grid_keys - image_keys
        missing_grids = image_keys - grid_keys

        if missing_images:
            print(f"发现 {len(missing_images)} 个网格数据缺少对应图片: {missing_images}")
        if missing_grids:
            print(f"发现 {len(missing_grids)} 张图片缺少网格数据: {missing_grids}")

        if missing_images or missing_grids:
            raise ValueError("图片与网格数据不匹配，请检查以下文件:\n"
                             f"缺失图片: {missing_images}\n"
                             f"缺失网格: {missing_grids}")

    def get_max_grid_size(self, img_name):
        max_row = 0
        max_col = 0
        for key in self.grid_dict.get(img_name, {}):
            row, col = map(int, key.split(','))
            max_row = max(max_row, row)
            max_col = max(max_col, col)
        return max_row, max_col

    def visualize_grids(self, img_name):
        src_img = self.srcImgs.get(img_name)
        if src_img is None or img_name not in self.grid_dict:
            return

        # 创建空白图像
        h, w = src_img.shape[:2]
        vis_img = np.zeros((h, w, 3), dtype=np.uint8)

        # 获取最大行列值
        max_row, max_col = self.get_max_grid_size(img_name)
        print(f"Image {img_name} has {max_row} rows and {max_col} columns.")

        # 计算居中偏移量
        cell_size = self.cell_size
        grid_width = max_col * cell_size
        grid_height = max_row * cell_size
        offset_x = (w - grid_width) // 2
        offset_y = (h - grid_height) // 2

        # 绘制居中理想网格点（绿色）
        for row in range(max_row + 1):
            for col in range(max_col + 1):
                x = int(col * cell_size) + offset_x
                y = int(row * cell_size) + offset_y
                if 0 <= x < w and 0 <= y < h:
                    cv2.circle(vis_img, (x, y), 5, (0, 255, 0), -1)
                    cv2.putText(
                        vis_img, f"{y},{x}", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 255, 0), 3)
                    if img_name not in self.dst_grid_dict:
                        self.dst_grid_dict[img_name] = {}
                    self.dst_grid_dict[img_name][f"{row},{col}"] = (x, y)

        # 获取网格的像素范围
        min_x, max_x = min(self.dst_grid_dict[img_name].values(), key=lambda x: x[0])[0], max(
            self.dst_grid_dict[img_name].values(), key=lambda x: x[0])[0]
        min_y, max_y = min(self.dst_grid_dict[img_name].values(), key=lambda x: x[1])[1], max(
            self.dst_grid_dict[img_name].values(), key=lambda x: x[1])[1]

        print(
            f"Image {img_name} has min_x = {min_x}, max_x = {max_x}, min_y = {min_y}, max_y = {max_y}.")

        size = [min_x, max_x, min_y, max_y]
        # 绘制实际网格点（红色）
        for key, (x, y) in self.grid_dict[img_name].items():
            cv2.circle(vis_img, (x, y), 5, (0, 0, 255), -1)
            row, col = map(int, key.split(','))
            cv2.putText(vis_img, f"{row},{col}", (x, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 255), 3)

        # 显示图像 图像可以缩放
        cv2.namedWindow(f'Grids for {img_name}', cv2.WINDOW_NORMAL)
        cv2.imshow(f'Grids for {img_name}', vis_img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        return vis_img

    def undistort_image(self, img_name, padding=100):
        """对图像进行校正
        Args:
            img_name: 图像名称
            src_pints: 源点坐标列表，格式为[(x1,y1), (x2,y2), ...]
            dst_points: 目标点坐标列表，格式为[(x1,y1), (x2,y2), ...]
        Returns:
            校正后的图像
        """
        # 获取原始图像
        src_img = self.srcImgs.get(img_name)
        if src_img is None:
            print(f"图像 {img_name} 不存在")
            return False

        h, w = src_img.shape[:2]
        cell_size = self.cell_size

        # 计算居中偏移量
        max_row, max_col = self.get_max_grid_size(img_name)  # 获取最大行列值
        grid_width = max_col * cell_size
        grid_height = max_row * cell_size
        offset_x = (w - grid_width) // 2
        offset_y = (h - grid_height) // 2

        for row in range(max_row + 1):
            for col in range(max_col + 1):
                x = int(col * cell_size) + offset_x
                y = int(row * cell_size) + offset_y
                if 0 <= x < w and 0 <= y < h:
                    if img_name not in self.dst_grid_dict:
                        self.dst_grid_dict[img_name] = {}
                    self.dst_grid_dict[img_name][f"{row},{col}"] = (x, y)

        # 获取网格的像素范围
        min_x, max_x = min(self.dst_grid_dict[img_name].values(), key=lambda x: x[0])[0], max(
            self.dst_grid_dict[img_name].values(), key=lambda x: x[0])[0]
        min_y, max_y = min(self.dst_grid_dict[img_name].values(), key=lambda x: x[1])[1], max(
            self.dst_grid_dict[img_name].values(), key=lambda x: x[1])[1]

        # 对应点对
        src_pints = []
        dst_points = []
        for key, (x, y) in self.grid_dict[img_name].items():
            if key in self.dst_grid_dict[img_name]:
                dst_x, dst_y = self.dst_grid_dict[img_name][key]
                dst_points.append((x, y))
                src_pints.append((dst_x, dst_y))
            else:
                print(f"Grid point {key} not found in dst_grid_dict in :  {img_name}.")
                return False

        # 转换点坐标格式
        src_points = np.array(src_pints)
        target_points = np.array(dst_points)
        source_x = src_points[:, 0]
        source_y = src_points[:, 1]
        target_x = target_points[:, 0]
        target_y = target_points[:, 1]

        def U(r):
            return r**2 * np.log(r + np.finfo(float).eps)

        N = len(src_points)
        P = np.hstack((np.ones((N, 1)), source_x.reshape(-1, 1),
                      source_y.reshape(-1, 1)))
        L = np.zeros((N + 3, N + 3))

        # 计算距离矩阵并填充L矩阵的左上角块
        source_x_grid = source_x.reshape(-1, 1)
        source_y_grid = source_y.reshape(-1, 1)
        dx = source_x_grid - source_x_grid.T
        dy = source_y_grid - source_y_grid.T
        dist = np.sqrt(dx**2 + dy**2)
        L[:N, :N] = U(dist)
        L[:N, N:] = P
        L[N:, :N] = P.T

        # 添加正则化项
        regularization_param = 1e-6
        L[:N, :N] += regularization_param * np.eye(N)
        Tx = np.vstack((target_x.reshape(-1, 1), np.zeros((3, 1))))
        Ty = np.vstack((target_y.reshape(-1, 1), np.zeros((3, 1))))
        wX = np.linalg.pinv(L) @ Tx
        wY = np.linalg.pinv(L) @ Ty

        # 提取权重
        alpha_x = wX[:N].flatten()
        beta_x = wX[N:].flatten()
        alpha_y = wY[:N].flatten()
        beta_y = wY[N:].flatten()

        # 添加 padding
        min_x = min_x-padding
        min_y = min_y-padding
        max_x = max_x+padding
        max_y = max_y+padding

        # 生成网格
        cols = np.arange(min_x, max_x + 1)  # 生成从min_x到max_x的整数序列
        rows = np.arange(min_y, max_y + 1)  # 生成从min_y到max_y的整数序列
        X, Y = np.meshgrid(cols, rows)  #

        # 计算校正后的坐标
        X_flat = X.ravel()
        Y_flat = Y.ravel()
        dX = X_flat[:, np.newaxis] - source_x
        dY = Y_flat[:, np.newaxis] - source_y
        r = np.sqrt(dX**2 + dY**2)
        U_r = r**2 * np.log(r + np.finfo(float).eps)

        X_transformed = beta_x[0] + beta_x[1]*X_flat + \
            beta_x[2]*Y_flat + np.dot(U_r, alpha_x)
        Y_transformed = beta_y[0] + beta_y[1]*X_flat + \
            beta_y[2]*Y_flat + np.dot(U_r, alpha_y)
        # 重塑为原始网格形状
        map_x = X_transformed.reshape(X.shape).astype(np.float32)
        map_y = Y_transformed.reshape(Y.shape).astype(np.float32)

        # 使用remap进行高效插值
        corrected_img = cv2.remap(src_img, map_x, map_y,
                                  interpolation=cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_CONSTANT)

        cv2.imwrite(f'./data/dst/{img_name}', corrected_img)
        print(f"Image {img_name} has been undistorted.")
        return corrected_img


if __name__ == "__main__":
    undistorter = Undistorter()
    # 只显示前5张图片的网格
    for img_name in list(undistorter.srcImgs.keys())[:]:
        vis_img = undistorter.undistort_image(img_name, 50)
