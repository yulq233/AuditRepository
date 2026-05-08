"""
爬虫服务模块
提供测试数据生成、Excel导入和模拟爬取功能
"""
import uuid
import random
import asyncio
import os
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, asdict
import logging

from app.core.database import get_db, get_db_cursor
from app.core.config import settings

logger = logging.getLogger(__name__)


@dataclass
class CrawlerTask:
    """爬虫任务"""
    id: str
    project_id: str
    platform: str
    status: str = 'pending'
    total_count: int = 0
    success_count: int = 0
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None


@dataclass
class MockVoucherData:
    """模拟凭证数据"""
    voucher_no: str
    voucher_date: str
    amount: float
    subject_code: str
    subject_name: str
    description: str
    counterparty: str


class MockCrawlerService:
    """
    模拟爬虫服务
    用于生成测试数据，模拟从公共审计平台获取凭证数据
    """

    # 模拟科目列表
    SUBJECTS = [
        ("1001", "库存现金"),
        ("1002", "银行存款"),
        ("1012", "其他货币资金"),
        ("1101", "交易性金融资产"),
        ("1121", "应收票据"),
        ("1122", "应收账款"),
        ("1123", "预付账款"),
        ("1221", "其他应收款"),
        ("1401", "材料采购"),
        ("1403", "原材料"),
        ("1405", "库存商品"),
        ("1601", "固定资产"),
        ("1602", "累计折旧"),
        ("2001", "短期借款"),
        ("2201", "应付票据"),
        ("2202", "应付账款"),
        ("2203", "预收账款"),
        ("2211", "应付职工薪酬"),
        ("2221", "应交税费"),
        ("4001", "实收资本"),
        ("4101", "盈余公积"),
        ("4103", "本年利润"),
        ("6001", "主营业务收入"),
        ("6051", "其他业务收入"),
        ("6401", "主营业务成本"),
        ("6402", "其他业务成本"),
        ("6601", "销售费用"),
        ("6602", "管理费用"),
        ("6603", "财务费用"),
    ]

    # 模拟交易对手
    COUNTERPARTIES = [
        "北京科技有限公司",
        "上海贸易有限公司",
        "广州制造有限公司",
        "深圳电子有限公司",
        "杭州网络技术有限公司",
        "成都物资有限公司",
        "武汉机械有限公司",
        "西安能源有限公司",
        "南京化工有限公司",
        "天津物流有限公司",
        "苏州纺织品有限公司",
        "青岛食品饮料有限公司",
        "大连海运有限公司",
        "厦门进出口有限公司",
        "重庆建材有限公司",
    ]

    # 模拟摘要模板
    DESCRIPTION_TEMPLATES = [
        "支付{counterparty}货款",
        "收到{counterparty}款项",
        "支付{counterparty}服务费",
        "{counterparty}采购款",
        "{counterparty}销售回款",
        "支付{counterparty}工程款",
        "{counterparty}往来款",
        "支付{counterparty}租金",
        "收到{counterparty}预付款",
        "{counterparty}结算款",
    ]

    def __init__(self):
        self._running_tasks: Dict[str, bool] = {}

    def generate_mock_voucher(self, index: int, year: int = 2024) -> MockVoucherData:
        """生成单个模拟凭证"""
        subject = random.choice(self.SUBJECTS)
        counterparty = random.choice(self.COUNTERPARTIES)
        description_template = random.choice(self.DESCRIPTION_TEMPLATES)

        # 生成凭证编号
        voucher_no = f"记-{year}-{str(index).zfill(4)}"

        # 生成日期（随机分布在年度内）
        start_date = datetime(year, 1, 1)
        random_days = random.randint(0, 364)
        voucher_date = start_date + timedelta(days=random_days)

        # 生成金额（根据科目类型调整范围）
        if subject[0].startswith('6'):  # 损益类科目
            amount = round(random.uniform(1000, 500000), 2)
        elif subject[0] in ['1']:  # 资产类
            amount = round(random.uniform(100, 10000000), 2)
        else:  # 负债和权益类
            amount = round(random.uniform(1000, 5000000), 2)

        return MockVoucherData(
            voucher_no=voucher_no,
            voucher_date=voucher_date.strftime('%Y-%m-%d'),
            amount=amount,
            subject_code=subject[0],
            subject_name=subject[1],
            description=description_template.format(counterparty=counterparty),
            counterparty=counterparty
        )

    def generate_mock_attachment(self, project_id: str, voucher_id: str, voucher: MockVoucherData) -> str:
        """
        生成模拟附件文件 - 图片格式凭证
        返回附件相对路径
        """
        from PIL import Image, ImageDraw, ImageFont
        import platform

        # 确保附件目录存在
        attachment_dir = os.path.join(settings.ATTACHMENT_PATH, project_id)
        os.makedirs(attachment_dir, exist_ok=True)

        # 生成文件名
        file_id = str(uuid.uuid4())
        file_name = f"{file_id}.png"
        file_path = os.path.join(attachment_dir, file_name)

        # 图片尺寸
        width = 800
        height = 600
        margin = 40

        # 创建白色背景图片
        img = Image.new('RGB', (width, height), 'white')
        draw = ImageDraw.Draw(img)

        # 尝试加载中文字体
        def get_font(size, bold=False):
            """获取字体，优先使用系统中文字体"""
            font_names = []
            if platform.system() == 'Windows':
                font_names = ['simhei.ttf', 'msyh.ttc', 'simsun.ttc']
            elif platform.system() == 'Darwin':  # macOS
                font_names = ['PingFang.ttc', 'STHeiti Light.ttc', 'Heiti SC.ttc']
            else:  # Linux
                font_names = ['NotoSansCJK-Regular.ttc', 'WenQuanYi Micro Hei.ttf', 'DejaVuSans.ttf']

            for font_name in font_names:
                try:
                    return ImageFont.truetype(font_name, size)
                except:
                    continue

            # 如果找不到任何字体，使用默认字体
            try:
                return ImageFont.truetype("arial.ttf", size)
            except:
                return ImageFont.load_default()

        # 字体设置
        font_title = get_font(28, bold=True)
        font_label = get_font(14, bold=True)
        font_content = get_font(14)
        font_amount = get_font(16, bold=True)

        # 颜色定义
        color_black = '#333333'
        color_gray = '#666666'
        color_border = '#cccccc'
        color_header_bg = '#f5f5f5'
        color_amount = '#cc0000'

        # 绘制标题
        title = "记账凭证"
        title_bbox = draw.textbbox((0, 0), title, font=font_title)
        title_width = title_bbox[2] - title_bbox[0]
        draw.text(((width - title_width) // 2, margin), title, font=font_title, fill=color_black)

        # 绘制标题下划线
        draw.line([(margin, margin + 45), (width - margin, margin + 45)], fill='#333333', width=2)

        # 表格参数
        table_top = margin + 70
        row_height = 35
        col1_width = 100  # 标签列宽度
        col2_width = 240  # 内容列1宽度
        col3_width = 100  # 标签列宽度
        col4_width = 280  # 内容列2宽度

        # 表格数据
        rows = [
            ('凭证编号', voucher.voucher_no, '凭证日期', voucher.voucher_date),
            ('科目代码', voucher.subject_code, '科目名称', voucher.subject_name),
            ('交易对手', voucher.counterparty, '', ''),
        ]

        y = table_top
        for row in rows:
            # 绘制单元格边框和背景
            draw.rectangle([(margin, y), (margin + col1_width, y + row_height)],
                          fill=color_header_bg, outline=color_border)
            draw.text((margin + 10, y + 8), row[0], font=font_label, fill=color_black)

            draw.rectangle([(margin + col1_width, y), (margin + col1_width + col2_width, y + row_height)],
                          fill='white', outline=color_border)
            draw.text((margin + col1_width + 10, y + 8), str(row[1]) if row[1] else '', font=font_content, fill=color_black)

            if row[2]:
                draw.rectangle([(margin + col1_width + col2_width, y),
                              (margin + col1_width + col2_width + col3_width, y + row_height)],
                             fill=color_header_bg, outline=color_border)
                draw.text((margin + col1_width + col2_width + 10, y + 8), row[2], font=font_label, fill=color_black)

                draw.rectangle([(margin + col1_width + col2_width + col3_width, y),
                              (width - margin, y + row_height)],
                             fill='white', outline=color_border)
                draw.text((margin + col1_width + col2_width + col3_width + 10, y + 8),
                         str(row[3]) if row[3] else '', font=font_content, fill=color_black)
            else:
                draw.rectangle([(margin + col1_width + col2_width, y), (width - margin, y + row_height)],
                              fill='white', outline=color_border)

            y += row_height

        # 金额行
        draw.rectangle([(margin, y), (margin + col1_width, y + row_height)],
                      fill=color_header_bg, outline=color_border)
        draw.text((margin + 10, y + 8), '金额', font=font_label, fill=color_black)

        draw.rectangle([(margin + col1_width, y), (width - margin, y + row_height)],
                      fill='white', outline=color_border)
        amount_str = f"¥ {voucher.amount:,.2f}"
        amount_bbox = draw.textbbox((0, 0), amount_str, font=font_amount)
        amount_width = amount_bbox[2] - amount_bbox[0]
        draw.text((width - margin - amount_width - 15, y + 8), amount_str, font=font_amount, fill=color_amount)

        y += row_height

        # 摘要行
        summary_height = 50
        draw.rectangle([(margin, y), (margin + col1_width, y + summary_height)],
                      fill=color_header_bg, outline=color_border)
        draw.text((margin + 10, y + 15), '摘要', font=font_label, fill=color_black)

        draw.rectangle([(margin + col1_width, y), (width - margin, y + summary_height)],
                      fill='white', outline=color_border)
        desc = voucher.description
        if len(desc) > 40:
            desc1 = desc[:40]
            desc2 = desc[40:]
            draw.text((margin + col1_width + 10, y + 10), desc1, font=font_content, fill=color_black)
            draw.text((margin + col1_width + 10, y + 30), desc2, font=font_content, fill=color_black)
        else:
            draw.text((margin + col1_width + 10, y + 15), desc, font=font_content, fill=color_black)

        y += summary_height

        # 绘制底部信息
        footer_y = y + 30
        draw.text((margin, footer_y), '制单人：系统生成', font=font_content, fill=color_gray)
        draw.text((margin, footer_y + 25), '审核人：__________', font=font_content, fill=color_gray)
        draw.text((margin, footer_y + 50), '记账人：__________', font=font_content, fill=color_gray)

        # 保存图片
        img.save(file_path, 'PNG', quality=95)

        # 返回相对路径
        return f"{project_id}/{file_name}"

    async def crawl_project_data(
        self,
        task_id: str,
        project_id: str,
        platform: str,
        count: int = 100,
        year: int = 2024
    ) -> CrawlerTask:
        """模拟爬取项目数据"""
        conn = get_db()
        task = CrawlerTask(
            id=task_id,
            project_id=project_id,
            platform=platform,
            status='running',
            started_at=datetime.now()
        )

        self._update_task(conn, task)

        try:
            success_count = 0
            batch_size = 10

            for i in range(0, count, batch_size):
                if not self._running_tasks.get(task_id, True):
                    task.status = 'stopped'
                    task.error_message = '任务被用户停止'
                    break

                batch_data = []
                for j in range(min(batch_size, count - i)):
                    voucher = self.generate_mock_voucher(i + j + 1, year)
                    voucher_id = str(uuid.uuid4())

                    attachment_path = self.generate_mock_attachment(
                        project_id, voucher_id, voucher
                    )

                    batch_data.append({
                        'id': voucher_id,
                        'project_id': project_id,
                        'voucher_no': voucher.voucher_no,
                        'voucher_date': voucher.voucher_date,
                        'amount': voucher.amount,
                        'subject_code': voucher.subject_code,
                        'subject_name': voucher.subject_name,
                        'description': voucher.description,
                        'counterparty': voucher.counterparty,
                        'attachment_path': attachment_path,
                        'raw_data': asdict(voucher),
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    })

                if batch_data:
                    self._insert_vouchers(conn, batch_data)
                    success_count += len(batch_data)

                    task.success_count = success_count
                    task.total_count = count
                    self._update_task(conn, task)

                await asyncio.sleep(0.5)

            if task.status == 'running':
                task.status = 'completed'
            task.finished_at = datetime.now()
            self._update_task(conn, task)

        except Exception as e:
            logger.error(f"爬取任务失败: {e}")
            task.status = 'failed'
            task.error_message = str(e)
            task.finished_at = datetime.now()
            self._update_task(conn, task)

        finally:
            self._running_tasks.pop(task_id, None)

        return task

    def _update_task(self, conn, task: CrawlerTask):
        """更新任务状态"""
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE crawler_tasks
            SET status = ?, total_count = ?, success_count = ?,
                error_message = ?, started_at = ?, finished_at = ?
            WHERE id = ?
        """, (
            task.status, task.total_count, task.success_count,
            task.error_message,
            task.started_at.isoformat() if task.started_at else None,
            task.finished_at.isoformat() if task.finished_at else None,
            task.id
        ))
        conn.commit()

    def _insert_vouchers(self, conn, vouchers: List[Dict]):
        """批量插入凭证"""
        cursor = conn.cursor()
        for v in vouchers:
            cursor.execute("""
                INSERT INTO vouchers
                (id, project_id, voucher_no, voucher_date, amount,
                 subject_code, subject_name, description, counterparty,
                 attachment_path, raw_data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                v['id'], v['project_id'], v['voucher_no'], v['voucher_date'],
                v['amount'], v['subject_code'], v['subject_name'],
                v['description'], v['counterparty'], v['attachment_path'],
                json.dumps(v['raw_data']), v['created_at'], v['updated_at']
            ))
        conn.commit()

    def stop_task(self, task_id: str):
        """停止任务"""
        self._running_tasks[task_id] = False


class ExcelImportCrawler:
    """
    Excel文件导入爬虫
    从上传的Excel文件中解析凭证数据
    """

    def __init__(self):
        self._running_tasks: Dict[str, bool] = {}

    async def import_from_excel(
        self,
        task_id: str,
        project_id: str,
        file_path: str,
        progress_callback: Optional[Callable] = None
    ) -> CrawlerTask:
        """
        从Excel文件导入凭证数据

        Args:
            task_id: 任务ID
            project_id: 项目ID
            file_path: Excel文件路径
            progress_callback: 进度回调函数
        """
        import pandas as pd

        conn = get_db()
        task = CrawlerTask(
            id=task_id,
            project_id=project_id,
            platform='excel_import',
            status='running',
            started_at=datetime.now()
        )

        self._update_task(conn, task)

        try:
            # 读取Excel文件
            df = pd.read_excel(file_path)
            total_count = len(df)

            # 标准化列名映射
            column_mapping = {
                '凭证号': 'voucher_no',
                '凭证编号': 'voucher_no',
                '日期': 'voucher_date',
                '凭证日期': 'voucher_date',
                '金额': 'amount',
                '科目代码': 'subject_code',
                '科目编码': 'subject_code',
                '科目名称': 'subject_name',
                '摘要': 'description',
                '交易对手': 'counterparty',
                '对方单位': 'counterparty',
            }

            # 重命名列
            df = df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns})

            # 必要列检查
            required_cols = ['voucher_no', 'voucher_date', 'amount']
            missing = [c for c in required_cols if c not in df.columns]
            if missing:
                raise ValueError(f"Excel缺少必要列: {missing}")

            success_count = 0
            batch_size = 50

            for i in range(0, total_count, batch_size):
                if not self._running_tasks.get(task_id, True):
                    task.status = 'stopped'
                    task.error_message = '任务被用户停止'
                    break

                batch = df.iloc[i:i+batch_size]
                batch_data = []

                for _, row in batch.iterrows():
                    try:
                        voucher_id = str(uuid.uuid4())

                        # 处理日期
                        voucher_date = row['voucher_date']
                        if pd.notna(voucher_date):
                            if isinstance(voucher_date, str):
                                pass
                            else:
                                voucher_date = str(voucher_date)[:10]

                        batch_data.append({
                            'id': voucher_id,
                            'project_id': project_id,
                            'voucher_no': str(row['voucher_no']),
                            'voucher_date': voucher_date,
                            'amount': float(row['amount']) if pd.notna(row['amount']) else 0,
                            'subject_code': str(row.get('subject_code', '')) if pd.notna(row.get('subject_code')) else '',
                            'subject_name': str(row.get('subject_name', '')) if pd.notna(row.get('subject_name')) else '',
                            'description': str(row.get('description', '')) if pd.notna(row.get('description')) else '',
                            'counterparty': str(row.get('counterparty', '')) if pd.notna(row.get('counterparty')) else '',
                            'attachment_path': None,
                            'raw_data': row.to_dict(),
                        })
                    except Exception as e:
                        logger.warning(f"解析行失败: {e}")
                        continue

                if batch_data:
                    self._insert_vouchers(conn, batch_data)
                    success_count += len(batch_data)

                    task.success_count = success_count
                    task.total_count = total_count
                    self._update_task(conn, task)

                    if progress_callback:
                        progress_callback(success_count, total_count)

            if task.status == 'running':
                task.status = 'completed'
            task.finished_at = datetime.now()
            self._update_task(conn, task)

        except Exception as e:
            logger.error(f"Excel导入失败: {e}")
            task.status = 'failed'
            task.error_message = str(e)
            task.finished_at = datetime.now()
            self._update_task(conn, task)

        finally:
            self._running_tasks.pop(task_id, None)

        return task

    def _update_task(self, conn, task: CrawlerTask):
        """更新任务状态"""
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE crawler_tasks
            SET status = ?, total_count = ?, success_count = ?,
                error_message = ?, started_at = ?, finished_at = ?
            WHERE id = ?
        """, (
            task.status, task.total_count, task.success_count,
            task.error_message,
            task.started_at.isoformat() if task.started_at else None,
            task.finished_at.isoformat() if task.finished_at else None,
            task.id
        ))
        conn.commit()

    def _insert_vouchers(self, conn, vouchers: List[Dict]):
        """批量插入凭证"""
        cursor = conn.cursor()
        for v in vouchers:
            cursor.execute("""
                INSERT INTO vouchers
                (id, project_id, voucher_no, voucher_date, amount,
                 subject_code, subject_name, description, counterparty,
                 attachment_path, raw_data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                v['id'], v['project_id'], v['voucher_no'], v['voucher_date'],
                v['amount'], v['subject_code'], v['subject_name'],
                v['description'], v['counterparty'], v['attachment_path'],
                json.dumps(v['raw_data'], default=str),
                datetime.now().isoformat(),
                datetime.now().isoformat()
            ))
        conn.commit()

    def stop_task(self, task_id: str):
        """停止任务"""
        self._running_tasks[task_id] = False


class PublicAuditPlatformCrawler:
    """
    公共审计平台爬虫基类

    提供与公共审计平台对接的框架，具体平台实现需要继承此类
    """

    def __init__(self):
        self._running_tasks: Dict[str, bool] = {}
        self._session = None

    async def login(self, username: str, password: str, platform_url: str) -> bool:
        """
        登录平台（子类实现具体逻辑）

        Args:
            username: 用户名
            password: 密码
            platform_url: 平台地址

        Returns:
            bool: 登录是否成功
        """
        raise NotImplementedError("子类需要实现login方法")

    async def fetch_vouchers(
        self,
        task_id: str,
        project_id: str,
        params: Dict[str, Any]
    ) -> CrawlerTask:
        """
        获取凭证数据（子类实现具体逻辑）

        Args:
            task_id: 任务ID
            project_id: 项目ID
            params: 查询参数

        Returns:
            CrawlerTask: 任务结果
        """
        raise NotImplementedError("子类需要实现fetch_vouchers方法")

    def stop_task(self, task_id: str):
        """停止任务"""
        self._running_tasks[task_id] = False


class CrawlerService:
    """爬虫服务入口"""

    def __init__(self):
        self.mock_crawler = MockCrawlerService()
        self.excel_crawler = ExcelImportCrawler()
        self._background_tasks: Dict[str, asyncio.Task] = {}

    def create_task(self, project_id: str, platform: str, count: int = 100) -> str:
        """创建爬虫任务"""
        task_id = str(uuid.uuid4())
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO crawler_tasks
            (id, project_id, platform, status, total_count, success_count)
            VALUES (?, ?, ?, 'pending', ?, 0)
        """, (task_id, project_id, platform, count))
        conn.commit()

        return task_id

    def start_crawl(
        self,
        task_id: str,
        project_id: str,
        platform: str = 'mock_platform',
        count: int = 100,
        year: int = 2024,
        file_path: str = None
    ):
        """启动爬取任务"""
        async def run_crawl():
            if platform == 'excel_import':
                if not file_path:
                    raise ValueError("Excel导入需要提供file_path参数")
                await self.excel_crawler.import_from_excel(
                    task_id, project_id, file_path
                )
            else:
                await self.mock_crawler.crawl_project_data(
                    task_id, project_id, platform, count, year
                )

        task = asyncio.create_task(run_crawl())
        self._background_tasks[task_id] = task

    def start_excel_import(self, task_id: str, project_id: str, file_path: str):
        """启动Excel导入任务"""
        async def run_import():
            await self.excel_crawler.import_from_excel(
                task_id, project_id, file_path
            )

        task = asyncio.create_task(run_import())
        self._background_tasks[task_id] = task

    def _format_datetime(self, dt) -> Optional[str]:
        """格式化datetime为ISO字符串"""
        if dt is None:
            return None
        if isinstance(dt, str):
            return dt
        return dt.isoformat() if hasattr(dt, 'isoformat') else str(dt)

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, project_id, platform, status, total_count,
                   success_count, error_message, started_at, finished_at
            FROM crawler_tasks WHERE id = ?
        """, (task_id,))

        row = cursor.fetchone()
        if row:
            return {
                'id': row[0],
                'project_id': row[1],
                'platform': row[2],
                'status': row[3],
                'total_count': row[4],
                'success_count': row[5],
                'error_message': row[6],
                'started_at': self._format_datetime(row[7]),
                'finished_at': self._format_datetime(row[8])
            }
        return None

    def get_project_tasks(self, project_id: str) -> List[Dict]:
        """获取项目的所有爬虫任务"""
        conn = get_db()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, project_id, platform, status, total_count,
                   success_count, error_message, started_at, finished_at
            FROM crawler_tasks
            WHERE project_id = ?
            ORDER BY started_at DESC
        """, (project_id,))

        rows = cursor.fetchall()
        return [
            {
                'id': row[0],
                'project_id': row[1],
                'platform': row[2],
                'status': row[3],
                'total_count': row[4],
                'success_count': row[5],
                'error_message': row[6],
                'started_at': self._format_datetime(row[7]),
                'finished_at': self._format_datetime(row[8])
            }
            for row in rows
        ]

    def stop_task(self, task_id: str) -> bool:
        """停止爬虫任务"""
        task = self._background_tasks.get(task_id)
        if task and not task.done():
            self.mock_crawler.stop_task(task_id)
            self.excel_crawler.stop_task(task_id)
            task.cancel()
            return True
        return False

    def get_available_platforms(self) -> List[Dict]:
        """获取可用平台列表"""
        return [
            {
                'id': 'mock_platform',
                'name': '模拟测试平台',
                'description': '用于生成测试数据（含凭证附件）',
                'supports_attachments': True,
                'config_fields': [
                    {'name': 'count', 'label': '生成数量', 'type': 'number', 'default': 100},
                    {'name': 'year', 'label': '会计年度', 'type': 'number', 'default': 2024}
                ]
            },
            {
                'id': 'excel_import',
                'name': 'Excel文件导入',
                'description': '从Excel文件导入凭证数据',
                'supports_attachments': False,
                'config_fields': [
                    {'name': 'file_path', 'label': '文件路径', 'type': 'file', 'required': True}
                ]
            },
            {
                'id': 'audit_public',
                'name': '公共审计平台（开发中）',
                'description': '对接真实公共审计平台（需配置登录凭证）',
                'supports_attachments': True,
                'config_fields': [
                    {'name': 'platform_url', 'label': '平台地址', 'type': 'text', 'required': True},
                    {'name': 'username', 'label': '用户名', 'type': 'text', 'required': True},
                    {'name': 'password', 'label': '密码', 'type': 'password', 'required': True}
                ],
                'status': 'coming_soon'
            }
        ]


# 单例
crawler_service = CrawlerService()
