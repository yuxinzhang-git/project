import cv2
import numpy as np
import struct, base64
from datetime import datetime
from aio import file2base64
from typing import List, Optional
from result import Object

def stitch_images(base64_frames: List[np.ndarray], objects: List[Object]=None, direction: str = 'vertical') -> Optional[np.ndarray]:
    decoded_frames = []
    
    # -----------------------------------------------------------
    # 步骤 1: Base64 解码并转换为 OpenCV 图像
    # -----------------------------------------------------------
    for i, base64_str in enumerate(base64_frames):
        try:
            img_bytes = base64.b64decode(base64_str)
            nparr = np.frombuffer(img_bytes, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                print(f"错误：无法解码 Base64 字符串 {i}。")
                return None
            
            decoded_frames.append(img)
            
        except Exception as e:
            print(f"处理 Base64 图片 {i} 时发生错误: {e}")
            return None

    if not decoded_frames:
        print("错误：解码后的图片列表为空。")
        return None

    # -----------------------------------------------------------
    # 步骤 2: 拼接图片
    # -----------------------------------------------------------
    h_ref, w_ref = decoded_frames[0].shape[:2]
    stitched_image = None
    
    if direction == 'horizontal':
        for i, frame in enumerate(decoded_frames):
            if frame.shape[0] != h_ref:
                print(f"错误：水平拼接要求高度一致。图片 0 高度 {h_ref}，图片 {i} 高度 {frame.shape[0]}")
                return None
        stitched_image = cv2.hconcat(decoded_frames)

    elif direction == 'vertical':
        for i, frame in enumerate(decoded_frames):
            if frame.shape[1] != w_ref:
                print(f"错误：垂直拼接要求宽度一致。图片 0 宽度 {w_ref}，图片 {i} 宽度 {frame.shape[1]}")
                return None
        stitched_image = cv2.vconcat(decoded_frames)
    
    else:
        print("错误：direction 参数必须是 'horizontal' 或 'vertical'。")
        return None

    if stitched_image is None:
        print("错误：拼接操作未成功返回图像。")
        return None
        
    # -----------------------------------------------------------
    # 步骤 3: 在最后一张图上绘制检测框（如果 objects 不为空）
    # -----------------------------------------------------------
    if objects is not None and len(objects) > 0:
        # 获取拼接后图像的尺寸
        stitch_h, stitch_w = stitched_image.shape[:2]
        
        # 获取单张图片的尺寸（用于计算偏移量）
        last_frame_h, last_frame_w = decoded_frames[-1].shape[:2]
        
        # 计算最后一张图片在拼接图中的位置偏移
        if direction == 'vertical':
            # 垂直拼接：最后一张图在底部
            offset_x = 0
            offset_y = stitch_h - last_frame_h
        else:  # horizontal
            # 水平拼接：最后一张图在右侧
            offset_x = stitch_w - last_frame_w
            offset_y = 0
        
        # 遍历所有 objects 并绘制边界框
        for obj in objects:
            # 获取归一化的边界框坐标 [xmin, ymin, xmax, ymax]
            box = obj.rectangle()
            if box is None or len(box) != 4:
                continue
            
            xmin, ymin, xmax, ymax = box
            
            # 将归一化坐标转换为最后一张图片的像素坐标
            x1 = int(xmin * last_frame_w)
            y1 = int(ymin * last_frame_h)
            x2 = int(xmax * last_frame_w)
            y2 = int(ymax * last_frame_h)
            
            # 加上偏移量，得到在拼接图中的绝对坐标
            x1_abs = x1 + offset_x
            y1_abs = y1 + offset_y
            x2_abs = x2 + offset_x
            y2_abs = y2 + offset_y
            
            # 绘制矩形框（绿色，线宽2）
            cv2.rectangle(stitched_image, (x1_abs, y1_abs), (x2_abs, y2_abs), (0, 255, 255), 2)
            
            # 如果有标签，也绘制标签文字
            label = obj.label()
            if label is not None and label == '停车':
                # 绘制标签背景
                label_text = 'stop vehicle'
                (text_w, text_h), baseline = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                cv2.rectangle(stitched_image, (x1_abs, y1_abs - text_h - baseline - 5), 
                             (x1_abs + text_w, y1_abs), (0, 255, 0), -1)
                # 绘制标签文字（黑色）
                cv2.putText(stitched_image, label_text, (x1_abs, y1_abs - baseline - 2), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
    # -----------------------------------------------------------
    # 步骤 4: 重新编码为字节数据并返回 Frame
    # -----------------------------------------------------------
    
    # 1. 重新编码为字节数据（JPEG 格式）
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 95] 
    _, img_encode = cv2.imencode('.jpg', stitched_image, encode_param)
    
    # 2. 返回一个新的 Frame 实例
    # 注意：由于输入是纯 Base64 字符串，我们无法继承原始的 'i' 和 '_occur'
    # 因此使用默认值 i=0 和当前时间戳
    return Frame(
        data=img_encode.tobytes(), 
        i=0, # 或您可以选择一个逻辑上的索引值
        occur='' # 让 Frame 构造函数自动设置当前时间
    )

def pad_image_to_square(image, pad_color=(0, 0, 0)):
    """
    为图像添加 padding，使其成为一个正方形。
    
    Args:
        image (np.ndarray): 输入的 cv2 图像。
        pad_color (tuple): padding 的颜色，默认为黑色 (0, 0, 0)。
        
    Returns:
        np.ndarray: 添加 padding 后的正方形图像。
    """
    # 获取图像的尺寸
    h, w = image.shape[:2]
    
    # 找出图像的最大边
    max_side = max(h, w)
    
    # 计算需要填充的 padding 尺寸
    pad_h_top, pad_h_bottom, pad_w_left, pad_w_right = 0, 0, 0, 0
    
    if h < max_side:
        # 高度小于最大边，需要填充垂直方向
        pad_h = max_side - h
        pad_h_top = pad_h // 2
        pad_h_bottom = pad_h - pad_h_top
    
    if w < max_side:
        # 宽度小于最大边，需要填充水平方向
        pad_w = max_side - w
        pad_w_left = pad_w // 2
        pad_w_right = pad_w - pad_w_left
        
    # 使用 cv2.copyMakeBorder() 添加 padding
    # BORDER_CONSTANT 表示使用固定的颜色填充
    padded_image = cv2.copyMakeBorder(
        image, 
        pad_h_top, 
        pad_h_bottom, 
        pad_w_left, 
        pad_w_right, 
        cv2.BORDER_CONSTANT, 
        value=pad_color
    )
    
    return padded_image

def get_jpeg_dimensions(data: bytes):
    """
    从内存中的JPEG数据中解析图像的宽和高。

    Args:
        data (bytes): 包含JPEG图像的二进制数据。

    Returns:
        tuple: (width, height) 如果成功解析，否则返回 None。
    """
    if data[0:2] != b'\xff\xd8':
        # 检查是否是JPEG文件的SOI（Start of Image）标记
        raise ValueError("Invalid JPEG data: missing SOI marker")

    # 从索引2开始，跳过 SOI 标记
    index = 2
    while index < len(data):
        marker = data[index:index+2]
        if marker[0] != 0xff:
            # JPEG标记总是以FF开头
            break
        
        # 检查是否是 SOF0 标记 (FF C0)
        if marker == b'\xff\xc0':
            # 找到 SOF0 标记，接下来的9个字节包含了我们所需的信息
            # 标记 FF C0 占 2 字节
            # 长度 占 2 字节
            # 精度 占 1 字节
            # 高度 占 2 字节
            # 宽度 占 2 字节
            # 我们可以直接跳过前5个字节（长度和精度），从第6个字节开始读
            # data[index+5] 是高度的第一个字节
            
            # 使用 struct.unpack 快速解析大端序的2字节整数
            # '>HH' 表示两个大端序的无符号短整数 (2字节)
            height, width = struct.unpack('>HH', data[index+5:index+9])
            return width, height

        # 如果不是 SOF0 标记，读取数据段的长度并跳过
        # 长度占2个字节，从当前标记的第3个字节开始
        segment_length = struct.unpack('>H', data[index+2:index+4])[0]
        
        # 标记本身占2字节，数据段长度占2字节
        # 因此需要跳过 2 (标记) + segment_length
        index += 2 + segment_length

    return None


class Frame:
    def __init__(self, data=None, i=0, occur=''):
        self.i = i
        self._occur = occur
        if self._occur == '':
            self._occur = datetime.now().isoformat()
        if data is not None:
            self._data = bytes(data)

    def read(self, data=None, filepath=None):
        if data is not None:
            self._data = bytes(data)
        if filepath is not None:
            with open(filepath, 'rb') as f:
                self._data = f.read()
        return

    def index(self):
        return self.i

    def occur(self):
        return self._occur

    def data(self):
        return self._data

    def clone(self):
        return Frame(self._data, self.i, self._occur)

    def image(self):
        np_array = np.frombuffer(self.data(), np.uint8)
        return cv2.imdecode(np_array, cv2.IMREAD_COLOR)

    def sharpen(self, strength=1):
        """
        对图像进行锐化处理，返回新的 Frame 对象，不改变原始数据
        
        Args:
            strength: 锐化强度，1为标准锐化，2为强锐化
            
        Returns:
            Frame: 包含锐化后图像的新 Frame 对象
        """
        # 解码图像
        img = self.image()
        
        # 定义锐化卷积核
        if strength == 1:
            # 标准锐化核
            kernel = np.array([[0, -1, 0],
                             [-1, 5, -1],
                             [0, -1, 0]], dtype=np.float32)
        else:
            # 强锐化核
            kernel = np.array([[-1, -1, -1],
                             [-1, 9, -1],
                             [-1, -1, -1]], dtype=np.float32)
        
        # 应用锐化滤波器
        sharpened = cv2.filter2D(img, -1, kernel)
        
        # 重新编码为JPEG
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 95]
        _, img_encode = cv2.imencode('.jpg', sharpened, encode_param)
        
        # 创建并返回新的 Frame 对象
        return Frame(data=img_encode.tobytes(), i=self.i, occur=self._occur)

    def deblur(self, kernel_size=15, angle=0):
        """
        去除运动模糊，返回新的 Frame 对象，不改变原始数据
        
        Args:
            kernel_size: 运动模糊核的大小，默认15
            angle: 运动模糊的角度（度数），0表示水平方向，默认0
            
        Returns:
            Frame: 包含去模糊后图像的新 Frame 对象
        """
        # 解码图像
        img = self.image()
        
        # 创建运动模糊核（Point Spread Function）
        def create_motion_blur_kernel(size, angle):
            """创建运动模糊核"""
            kernel = np.zeros((size, size))
            center = size // 2
            
            # 计算角度的弧度
            angle_rad = np.deg2rad(angle)
            cos_val = np.cos(angle_rad)
            sin_val = np.sin(angle_rad)
            
            # 在核中心画一条线
            for i in range(size):
                offset = i - center
                y = int(center + offset * sin_val)
                x = int(center + offset * cos_val)
                if 0 <= y < size and 0 <= x < size:
                    kernel[y, x] = 1
            
            # 归一化
            kernel = kernel / np.sum(kernel)
            return kernel
        
        # 创建运动模糊核
        psf = create_motion_blur_kernel(kernel_size, angle)
        
        # 使用维纳滤波进行反卷积
        # 首先对图像和PSF进行傅里叶变换
        img_float = img.astype(np.float32) / 255.0
        deblurred_channels = []
        
        for channel in range(img_float.shape[2]):
            # 获取单通道
            img_channel = img_float[:, :, channel]
            
            # 傅里叶变换
            img_fft = np.fft.fft2(img_channel)
            psf_fft = np.fft.fft2(psf, s=img_channel.shape)
            
            # 维纳滤波
            # 添加噪声功率比（NSR）来稳定反卷积
            nsr = 0.01  # 噪声信号比
            psf_conj = np.conj(psf_fft)
            deblurred_fft = (psf_conj / (np.abs(psf_fft)**2 + nsr)) * img_fft
            
            # 逆傅里叶变换
            deblurred_channel = np.fft.ifft2(deblurred_fft)
            deblurred_channel = np.real(deblurred_channel)
            
            # 限制范围到 [0, 1]
            deblurred_channel = np.clip(deblurred_channel, 0, 1)
            deblurred_channels.append(deblurred_channel)
        
        # 合并通道
        deblurred = np.stack(deblurred_channels, axis=2)
        deblurred = (deblurred * 255).astype(np.uint8)
        
        # 应用轻微的双边滤波来减少噪声
        deblurred = cv2.bilateralFilter(deblurred, 5, 50, 50)
        
        # 重新编码为JPEG
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 95]
        _, img_encode = cv2.imencode('.jpg', deblurred, encode_param)
        
        # 创建并返回新的 Frame 对象
        return Frame(data=img_encode.tobytes(), i=self.i, occur=self._occur)

    def img64(self):
        return file2base64(data=self._data)

    def resize(self, dim):
        np_array = np.frombuffer(self.data(), np.uint8)
        img = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        return cv2.resize(img, dim)

    def resize64(self, dim):
        resized = self.resize(dim)
        # print('resize:',resized.shape)
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 95]
        _,img_encode = cv2.imencode('.jpg', resized, encode_param)
        return base64.b64encode(img_encode).decode('utf-8')

    def crop(self, rect=None, center=None, dim=None, resize=None, extend=None):
        img = self.image()
        h,w,_ = img.shape
        # print(rect, center, dim)
        x1,y1,x2,y2 = 0,0,w-1,h-1
        if rect is not None:
            xmin,ymin,xmax,ymax = rect
            if extend is not None:
                ex,ey = (xmax-xmin)*extend,(ymax-ymin)*extend
                xmin,ymin,xmax,ymax = xmin-ex,ymin-ey,xmax+ex,ymax+ey
                x,y = xmin+(xmax-xmin)/2,ymin+(ymax-ymin)/2
                c = max(int((xmax-xmin)*w/2),int((ymax-ymin)*h/2))
                # 不能低于64像素
                c = max(c, 32)
                xmin,ymin,xmax,ymax = x-c/w,y-c/h,x+c/w,y+c/h
                if xmax > 1.0:
                    xmin,xmax = xmin-(xmax-1.0),1.0
                if xmin < 0:
                    xmin,xmax = 0,xmax+(-xmin)
                if ymax > 1.0:
                    ymin,ymax = ymin-(ymax-1.0),1.0
                if ymin < 0:
                    ymin,ymax = 0,ymax+(-ymin)
        elif center is not None and dim is not None:
            xmin,ymin,xmax,ymax = center[0]-dim[0]/2,center[1]-dim[1]/2,center[0]+dim[0]/2,center[1]+dim[1]/2
        x1,y1,x2,y2 = int(max(0,xmin*w)),int(max(0,ymin*h)),int(min(w,xmax*w)),int(min(h,ymax*h))
        # print(x1,y1,x2,y2)
        if resize is None:
            return img[y1:y2,x1:x2]
        # padded = pad_image_to_square(img[y1:y2,x1:x2])
        return cv2.resize(img[y1:y2,x1:x2], resize,interpolation=cv2.INTER_CUBIC)

    def crop64(self, rect=None, center=None, dim=None, resize=None, extend=None):
        cropped = self.crop(rect, center, dim, resize, extend)
        # print('crop:',cropped.shape)
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 95]
        _,img_encode = cv2.imencode('.jpg', cropped, encode_param)
        return base64.b64encode(img_encode).decode('utf-8')
    
    def dict(self):
        return {
            'timestamp': self.i,
            'occur': self._occur,
            'image': file2base64(data=self._data),
        }