import numpy as np
import cv2
import os
import json


def generate_ellipse_points(center, axes, angle, num_points=100):
    """
    生成椭圆边界上均匀分布的点

    参数:
    center: 椭圆中心点坐标 (x, y)
    axes: 椭圆的长短轴 (a, b)
    angle: 椭圆旋转角度（度）
    num_points: 生成的点数量

    返回:
    points: 椭圆边界上的点坐标数组，形状为 (num_points, 2)
    """
    # 将角度转换为弧度
    angle_rad = np.deg2rad(angle)

    # 生成参数方程的参数 t
    t = np.linspace(0, 2*np.pi, num_points)

    # 计算未旋转椭圆上的点
    x0 = axes[0] * np.cos(t)
    y0 = axes[1] * np.sin(t)

    # 旋转点
    x = center[0] + x0 * np.cos(angle_rad) - y0 * np.sin(angle_rad)
    y = center[1] + x0 * np.sin(angle_rad) + y0 * np.cos(angle_rad)

    # 组合成坐标点数组
    points = np.column_stack((x, y))

    return points


def main():
    # 创建数据目录（如果不存在）
    data_dir = "./data"
    src_dir = os.path.join(data_dir, "src")
    ellipse_info_dir = os.path.join(data_dir, "ellipse_info")

    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"创建目录: {data_dir}")

    if not os.path.exists(src_dir):
        os.makedirs(src_dir)
        print(f"创建目录: {src_dir}")
        print("请在 ./data/src/ 目录中放入图像文件")
        return

    if not os.path.exists(ellipse_info_dir):
        os.makedirs(ellipse_info_dir)
        print(f"创建目录: {ellipse_info_dir}")
        print("请先运行 mainWindow.py 生成椭圆信息")
        return

    # 获取所有图像文件
    image_files = []
    for dirname, _, filenames in os.walk(src_dir):
        for filename in filenames:
            if filename.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                image_files.append(os.path.join(dirname, filename))

    if not image_files:
        print("未找到图像文件，请在 ./data/src/ 目录中放入图像文件")
        return

    # 处理每个图像文件
    for img_path in image_files:
        img_name = os.path.basename(img_path)
        img_name_without_ext = os.path.splitext(img_name)[0]

        # 读取原始图像
        img = cv2.imread(img_path)
        if img is None:
            print(f"无法读取图像: {img_path}")
            continue

        # 旋转图像（与 mainWindow.py 保持一致）
        img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)
        display_img = img.copy()

        # 查找对应的椭圆信息文件
        for roi_index in range(1, 5):  # ROI_1 到 ROI_4
            ellipse_file = os.path.join(
                ellipse_info_dir, f"{img_name_without_ext}-roi{roi_index}-ellipse.json")

            if not os.path.exists(ellipse_file):
                continue

            # 读取椭圆信息（JSON格式）
            with open(ellipse_file, 'r') as f:
                ellipse_info = json.load(f)
                center = tuple(ellipse_info["center"])
                axes = tuple(ellipse_info["axes"])
                angle = ellipse_info["angle"]

            # 生成椭圆边界点
            ellipse_points = generate_ellipse_points(
                center, axes, angle, num_points=100)

            # 使用OpenCV绘制椭圆
            cv2.ellipse(display_img,
                        (int(center[0]), int(center[1])),
                        (int(axes[0]), int(axes[1])),
                        angle, 0, 360, (0, 255, 0), 2)

            # 绘制生成的椭圆点
            for point in ellipse_points:
                x, y = point
                cv2.circle(display_img, (int(x), int(y)), 2, (0, 0, 255), -1)

            # 在椭圆中心显示ROI索引
            cv2.putText(display_img, f"ROI {roi_index}",
                        (int(center[0]), int(center[1])),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)

        # 使用imshow显示图像（OpenCV窗口）
        cv2.namedWindow(f"图像: {img_name}", cv2.WINDOW_NORMAL)
        cv2.imshow(f"图像: {img_name}", display_img)
        print(f"显示图像: {img_name}，按任意键继续...")
        cv2.waitKey(0)

    # 关闭所有OpenCV窗口
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
    print("处理完成")
