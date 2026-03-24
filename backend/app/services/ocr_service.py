"""
OCR服务
支持PaddleOCR和EasyOCR
"""
import os
import re
import json
import hashlib
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import uuid

from app.core.config import settings
from app.core.database import get_db_cursor, get_db


@dataclass
class OCRResult:
    """OCR识别结果"""
    voucher_no: Optional[str] = None
    voucher_date: Optional[str] = None
    amount: Optional[float] = None
    counterparty: Optional[str] = None
    description: Optional[str] = None
    signatures: List[Dict[str, Any]] = field(default_factory=list)
    raw_text: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    provider: str = ""
    raw_result: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TextBlock:
    """文本块"""
    text: str
    confidence: float
    bbox: List[List[int]]  # 四个角坐标 [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]


class OCRBackend(ABC):
    """OCR后端基类"""

    @abstractmethod
    def recognize(self, image_path: str) -> List[TextBlock]:
        """识别图片中的文字"""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """检查OCR引擎是否可用"""
        pass


class PaddleOCRBackend(OCRBackend):
    """PaddleOCR后端"""

    def __init__(self, lang: str = "ch", use_gpu: bool = False):
        self.lang = lang
        self.use_gpu = use_gpu
        self._ocr = None

    @property
    def ocr(self):
        """懒加载OCR实例"""
        if self._ocr is None:
            try:
                from paddleocr import PaddleOCR
                self._ocr = PaddleOCR(
                    use_angle_cls=True,
                    lang=self.lang,
                    use_gpu=self.use_gpu,
                    show_log=False
                )
            except ImportError:
                raise RuntimeError("请安装PaddleOCR: pip install paddleocr paddlepaddle")
        return self._ocr

    def recognize(self, image_path: str) -> List[TextBlock]:
        """识别图片中的文字"""
        result = self.ocr.ocr(image_path, cls=True)

        blocks = []
        if result and result[0]:
            for item in result[0]:
                bbox = item[0]
                text = item[1][0]
                confidence = item[1][1]

                blocks.append(TextBlock(
                    text=text,
                    confidence=confidence,
                    bbox=[[int(p[0]), int(p[1])] for p in bbox]
                ))

        return blocks

    def is_available(self) -> bool:
        """检查PaddleOCR是否可用"""
        try:
            import paddleocr
            return True
        except ImportError:
            return False


class EasyOCRBackend(OCRBackend):
    """EasyOCR后端"""

    def __init__(self, lang: List[str] = None, use_gpu: bool = False):
        self.lang = lang or ["ch_sim", "en"]
        self.use_gpu = use_gpu
        self._reader = None

    @property
    def reader(self):
        """懒加载Reader实例"""
        if self._reader is None:
            try:
                import easyocr
                self._reader = easyocr.Reader(self.lang, gpu=self.use_gpu)
            except ImportError:
                raise RuntimeError("请安装EasyOCR: pip install easyocr")
        return self._reader

    def recognize(self, image_path: str) -> List[TextBlock]:
        """识别图片中的文字"""
        result = self.reader.readtext(image_path)

        blocks = []
        for item in result:
            bbox = item[0]
            text = item[1]
            confidence = item[2]

            blocks.append(TextBlock(
                text=text,
                confidence=confidence,
                bbox=[[int(p[0]), int(p[1])] for p in bbox]
            ))

        return blocks

    def is_available(self) -> bool:
        """检查EasyOCR是否可用"""
        try:
            import easyocr
            return True
        except ImportError:
            return False


class MockOCRBackend(OCRBackend):
    """模拟OCR后端（用于测试）"""

    def recognize(self, image_path: str) -> List[TextBlock]:
        """返回模拟数据"""
        return [
            TextBlock(text="记-001", confidence=0.95, bbox=[]),
            TextBlock(text="2024-01-15", confidence=0.98, bbox=[]),
            TextBlock(text="¥12,345.67", confidence=0.96, bbox=[]),
        ]

    def is_available(self) -> bool:
        return True


class FieldExtractor:
    """字段提取器"""

    # 凭证号正则
    VOUCHER_NO_PATTERNS = [
        r'记[—\-]?(\d+)',
        r'凭证[号]?[：:]\s*(\d+)',
        r'[Nn]o[．.:：]\s*(\d+)',
        r'(\d{4,})',
    ]

    # 日期正则
    DATE_PATTERNS = [
        r'(\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日]?)',
        r'(\d{1,2}[-/]\d{1,2}[-/]\d{4})',
    ]

    # 金额正则
    AMOUNT_PATTERNS = [
        r'[¥￥]?\s*([\d,]+\.?\d*)',
        r'金额[：:]\s*([\d,]+\.?\d*)',
        r'大写[：:]\s*(.+?)(?=\s|$)',
    ]

    @classmethod
    def extract_voucher_no(cls, text_blocks: List[TextBlock]) -> Optional[str]:
        """提取凭证号"""
        for block in text_blocks:
            for pattern in cls.VOUCHER_NO_PATTERNS:
                match = re.search(pattern, block.text)
                if match:
                    return match.group(1) if match.lastindex else match.group(0)
        return None

    @classmethod
    def extract_date(cls, text_blocks: List[TextBlock]) -> Optional[str]:
        """提取日期"""
        for block in text_blocks:
            for pattern in cls.DATE_PATTERNS:
                match = re.search(pattern, block.text)
                if match:
                    date_str = match.group(1)
                    # 标准化日期格式
                    date_str = date_str.replace('年', '-').replace('月', '-').replace('日', '')
                    date_str = date_str.replace('/', '-')
                    return date_str
        return None

    @classmethod
    def extract_amount(cls, text_blocks: List[TextBlock]) -> Optional[float]:
        """提取金额"""
        amounts = []
        for block in text_blocks:
            for pattern in cls.AMOUNT_PATTERNS[:2]:  # 只检查数字格式
                match = re.search(pattern, block.text)
                if match:
                    try:
                        amount_str = match.group(1).replace(',', '')
                        amount = float(amount_str)
                        if amount > 0:
                            amounts.append((amount, block.confidence))
                    except ValueError:
                        continue

        if amounts:
            # 返回置信度最高的金额
            amounts.sort(key=lambda x: x[1], reverse=True)
            return amounts[0][0]

        return None

    @classmethod
    def extract_counterparty(cls, text_blocks: List[TextBlock]) -> Optional[str]:
        """提取交易对手"""
        # 常见关键词
        keywords = ['公司', '有限', '集团', '银行', '供应商', '客户', '单位']

        for block in text_blocks:
            text = block.text
            if any(kw in text for kw in keywords) and len(text) > 4:
                return text.strip()

        return None

    @classmethod
    def extract_description(cls, text_blocks: List[TextBlock]) -> Optional[str]:
        """提取摘要"""
        # 通常摘要包含特定关键词
        keywords = ['摘要', '事由', '用途', '内容', '说明']

        for i, block in enumerate(text_blocks):
            text = block.text
            for kw in keywords:
                if kw in text:
                    # 返回关键词后的内容或下一个文本块
                    idx = text.find(kw) + len(kw)
                    if idx < len(text):
                        return text[idx:].strip('：: ')
                    elif i + 1 < len(text_blocks):
                        return text_blocks[i + 1].text

        return None


class OCRService:
    """OCR服务"""

    def __init__(self, provider: str = "paddleocr"):
        self.provider = provider
        self._backend = None
        self.extractor = FieldExtractor()

    @property
    def backend(self) -> OCRBackend:
        """获取OCR后端"""
        if self._backend is None:
            if self.provider == "paddleocr":
                self._backend = PaddleOCRBackend(lang=settings.OCR_LANGUAGE)
            elif self.provider == "easyocr":
                self._backend = EasyOCRBackend()
            elif self.provider == "mock":
                self._backend = MockOCRBackend()
            else:
                raise ValueError(f"不支持的OCR提供商: {self.provider}")

        return self._backend

    def preprocess_image(self, image_path: str) -> str:
        """
        图像预处理
        返回处理后的图片路径
        """
        try:
            import cv2
            import numpy as np

            # 读取图片
            img = cv2.imread(image_path)
            if img is None:
                return image_path

            # 转灰度
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # 降噪
            denoised = cv2.fastNlMeansDenoising(gray)

            # 增强对比度
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(denoised)

            # 保存处理后的图片
            processed_path = image_path.replace('.', '_processed.')
            cv2.imwrite(processed_path, enhanced)

            return processed_path

        except ImportError:
            return image_path
        except Exception:
            return image_path

    def recognize(self, image_path: str, preprocess: bool = True) -> OCRResult:
        """识别凭证图片"""
        # 检查文件是否存在
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"图片不存在: {image_path}")

        # 预处理
        if preprocess:
            processed_path = self.preprocess_image(image_path)
        else:
            processed_path = image_path

        # OCR识别
        text_blocks = self.backend.recognize(processed_path)

        # 提取关键字段
        voucher_no = self.extractor.extract_voucher_no(text_blocks)
        voucher_date = self.extractor.extract_date(text_blocks)
        amount = self.extractor.extract_amount(text_blocks)
        counterparty = self.extractor.extract_counterparty(text_blocks)
        description = self.extractor.extract_description(text_blocks)

        # 计算平均置信度
        if text_blocks:
            avg_confidence = sum(b.confidence for b in text_blocks) / len(text_blocks)
        else:
            avg_confidence = 0.0

        # 构建原始文本
        raw_text = [
            {
                "text": b.text,
                "confidence": b.confidence,
                "bbox": b.bbox
            }
            for b in text_blocks
        ]

        return OCRResult(
            voucher_no=voucher_no,
            voucher_date=voucher_date,
            amount=amount,
            counterparty=counterparty,
            description=description,
            raw_text=raw_text,
            confidence=avg_confidence,
            provider=self.provider
        )

    def save_result(self, voucher_id: str, result: OCRResult) -> str:
        """保存OCR结果到数据库"""
        result_id = str(uuid.uuid4())

        with get_db_cursor() as cursor:
            # 检查是否已有结果
            cursor.execute(
                "SELECT id FROM voucher_ocr_results WHERE voucher_id = ?",
                [voucher_id]
            )
            existing = cursor.fetchone()

            if existing:
                # 更新现有记录
                cursor.execute(
                    """
                    UPDATE voucher_ocr_results SET
                        ocr_provider = ?,
                        voucher_no = ?,
                        voucher_date = ?,
                        amount = ?,
                        counterparty = ?,
                        description = ?,
                        raw_text = ?,
                        confidence = ?,
                        raw_result = ?
                    WHERE voucher_id = ?
                    """,
                    [
                        result.provider,
                        result.voucher_no,
                        result.voucher_date,
                        result.amount,
                        result.counterparty,
                        result.description,
                        json.dumps(result.raw_text, ensure_ascii=False),
                        result.confidence,
                        json.dumps(result.raw_result, ensure_ascii=False),
                        voucher_id
                    ]
                )
                result_id = existing[0]
            else:
                # 插入新记录
                cursor.execute(
                    """
                    INSERT INTO voucher_ocr_results
                    (id, voucher_id, ocr_provider, voucher_no, voucher_date,
                     amount, counterparty, description, raw_text, confidence, raw_result)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [
                        result_id,
                        voucher_id,
                        result.provider,
                        result.voucher_no,
                        result.voucher_date,
                        result.amount,
                        result.counterparty,
                        result.description,
                        json.dumps(result.raw_text, ensure_ascii=False),
                        result.confidence,
                        json.dumps(result.raw_result, ensure_ascii=False)
                    ]
                )

            get_db().commit()

        return result_id

    def get_cached_result(self, voucher_id: str) -> Optional[OCRResult]:
        """获取缓存的OCR结果"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT voucher_no, voucher_date, amount, counterparty,
                       description, raw_text, confidence, ocr_provider, raw_result
                FROM voucher_ocr_results
                WHERE voucher_id = ?
                """,
                [voucher_id]
            )
            row = cursor.fetchone()

            if not row:
                return None

            return OCRResult(
                voucher_no=row[0],
                voucher_date=row[1],
                amount=float(row[2]) if row[2] else None,
                counterparty=row[3],
                description=row[4],
                raw_text=json.loads(row[5]) if isinstance(row[5], str) else row[5],
                confidence=float(row[6]) if row[6] else 0.0,
                provider=row[7],
                raw_result=json.loads(row[8]) if isinstance(row[8], str) else row[8]
            )

    def is_available(self) -> bool:
        """检查OCR服务是否可用"""
        return self.backend.is_available()


# 全局OCR服务实例
ocr_service = OCRService(provider=settings.OCR_PROVIDER)