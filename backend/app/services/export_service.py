"""
导出服务
支持导出抽凭结果、工作底稿等到Excel/PDF
"""
import io
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import uuid

from app.core.database import get_db_cursor
from app.core.config import settings


class ExcelExporter:
    """Excel导出器"""

    def __init__(self):
        try:
            import pandas as pd
            from openpyxl import Workbook
            from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
            self.pd = pd
            self.Workbook = Workbook
            self.styles = {
                'Font': Font,
                'Alignment': Alignment,
                'Border': Border,
                'Side': Side,
                'PatternFill': PatternFill
            }
            self.available = True
        except ImportError:
            self.available = False

    def export_sampling_results(
        self,
        project_id: str,
        rule_id: Optional[str] = None,
        include_details: bool = True
    ) -> bytes:
        """
        导出抽凭结果到Excel

        Args:
            project_id: 项目ID
            rule_id: 规则ID（可选，不指定则导出全部）
            include_details: 是否包含详细信息

        Returns:
            Excel文件字节
        """
        if not self.available:
            raise RuntimeError("请安装pandas和openpyxl: pip install pandas openpyxl")

        # 查询数据
        with get_db_cursor() as cursor:
            # 获取项目信息
            cursor.execute(
                "SELECT name FROM projects WHERE id = ?",
                [project_id]
            )
            project_row = cursor.fetchone()
            project_name = project_row[0] if project_row else "未知项目"

            # 构建查询
            query = """
                SELECT
                    v.voucher_no,
                    v.voucher_date,
                    v.amount,
                    v.subject_code,
                    v.subject_name,
                    v.description,
                    v.counterparty,
                    s.risk_score,
                    s.reason,
                    sr.name as rule_name,
                    s.sampled_at
                FROM samples s
                JOIN vouchers v ON s.voucher_id = v.id
                LEFT JOIN sampling_rules sr ON s.rule_id = sr.id
                WHERE s.project_id = ?
            """
            params = [project_id]

            if rule_id:
                query += " AND s.rule_id = ?"
                params.append(rule_id)

            query += " ORDER BY s.sampled_at DESC"

            cursor.execute(query, params)
            rows = cursor.fetchall()

        # 创建DataFrame
        columns = [
            "凭证编号", "凭证日期", "金额", "科目代码",
            "科目名称", "摘要", "交易对手", "风险分数",
            "抽取原因", "规则名称", "抽取时间"
        ]

        data = []
        for row in rows:
            data.append({
                "凭证编号": row[0],
                "凭证日期": str(row[1]) if row[1] else "",
                "金额": float(row[2]) if row[2] else 0,
                "科目代码": row[3] or "",
                "科目名称": row[4] or "",
                "摘要": row[5] or "",
                "交易对手": row[6] or "",
                "风险分数": float(row[7]) if row[7] else "",
                "抽取原因": row[8] or "",
                "规则名称": row[9] or "",
                "抽取时间": str(row[10]) if row[10] else ""
            })

        df = self.pd.DataFrame(data)

        # 导出到Excel
        output = io.BytesIO()

        with self.pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='抽凭结果', index=False)

            # 获取工作簿和工作表
            workbook = writer.book
            worksheet = writer.sheets['抽凭结果']

            # 设置样式
            header_font = self.styles['Font'](bold=True, size=11)
            header_fill = self.styles['PatternFill'](
                start_color='4472C4',
                end_color='4472C4',
                fill_type='solid'
            )
            header_font_white = self.styles['Font'](bold=True, color='FFFFFF', size=11)
            thin_border = self.styles['Border'](
                left=self.styles['Side'](style='thin'),
                right=self.styles['Side'](style='thin'),
                top=self.styles['Side'](style='thin'),
                bottom=self.styles['Side'](style='thin')
            )

            # 设置表头样式
            for cell in worksheet[1]:
                cell.font = header_font_white
                cell.fill = header_fill
                cell.alignment = self.styles['Alignment'](horizontal='center', vertical='center')
                cell.border = thin_border

            # 设置数据区域样式
            for row in worksheet.iter_rows(min_row=2, max_row=len(data) + 1):
                for cell in row:
                    cell.border = thin_border
                    cell.alignment = self.styles['Alignment'](vertical='center')

            # 调整列宽
            column_widths = {
                'A': 15,  # 凭证编号
                'B': 12,  # 凭证日期
                'C': 12,  # 金额
                'D': 12,  # 科目代码
                'E': 20,  # 科目名称
                'F': 30,  # 摘要
                'G': 20,  # 交易对手
                'H': 10,  # 风险分数
                'I': 25,  # 抽取原因
                'J': 15,  # 规则名称
                'K': 20,  # 抽取时间
            }

            for col, width in column_widths.items():
                worksheet.column_dimensions[col].width = width

        output.seek(0)
        return output.getvalue()

    def export_vouchers(
        self,
        project_id: str,
        filters: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """
        导出凭证列表到Excel

        Args:
            project_id: 项目ID
            filters: 筛选条件

        Returns:
            Excel文件字节
        """
        if not self.available:
            raise RuntimeError("请安装pandas和openpyxl: pip install pandas openpyxl")

        # 查询数据
        with get_db_cursor() as cursor:
            query = """
                SELECT
                    voucher_no, voucher_date, amount,
                    subject_code, subject_name, description,
                    counterparty, created_at
                FROM vouchers
                WHERE project_id = ?
            """
            params = [project_id]

            # 应用筛选条件
            if filters:
                if filters.get('subject_code'):
                    query += " AND subject_code = ?"
                    params.append(filters['subject_code'])
                if filters.get('start_date'):
                    query += " AND voucher_date >= ?"
                    params.append(filters['start_date'])
                if filters.get('end_date'):
                    query += " AND voucher_date <= ?"
                    params.append(filters['end_date'])

            query += " ORDER BY voucher_date, voucher_no"

            cursor.execute(query, params)
            rows = cursor.fetchall()

        # 创建DataFrame
        data = []
        for row in rows:
            data.append({
                "凭证编号": row[0],
                "凭证日期": str(row[1]) if row[1] else "",
                "金额": float(row[2]) if row[2] else 0,
                "科目代码": row[3] or "",
                "科目名称": row[4] or "",
                "摘要": row[5] or "",
                "交易对手": row[6] or "",
                "创建时间": str(row[7]) if row[7] else ""
            })

        df = self.pd.DataFrame(data)

        # 导出到Excel
        output = io.BytesIO()
        df.to_excel(output, index=False, sheet_name='凭证列表')
        output.seek(0)

        return output.getvalue()

    def export_project_summary(
        self,
        project_id: str
    ) -> bytes:
        """
        导出项目汇总报告

        Args:
            project_id: 项目ID

        Returns:
            Excel文件字节
        """
        if not self.available:
            raise RuntimeError("请安装pandas和openpyxl: pip install pandas openpyxl")

        output = io.BytesIO()

        with self.pd.ExcelWriter(output, engine='openpyxl') as writer:
            # 1. 项目概况
            with get_db_cursor() as cursor:
                cursor.execute(
                    "SELECT name, description, status, created_at FROM projects WHERE id = ?",
                    [project_id]
                )
                project = cursor.fetchone()

                cursor.execute(
                    "SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM vouchers WHERE project_id = ?",
                    [project_id]
                )
                voucher_stats = cursor.fetchone()

                cursor.execute(
                    "SELECT COUNT(*) FROM samples WHERE project_id = ?",
                    [project_id]
                )
                sample_count = cursor.fetchone()[0]

            overview_data = {
                "项目名称": [project[0]],
                "项目描述": [project[1] or ""],
                "项目状态": [project[2]],
                "创建时间": [str(project[3])],
                "凭证总数": [voucher_stats[0]],
                "凭证总金额": [float(voucher_stats[1])],
                "抽样数量": [sample_count]
            }

            df_overview = self.pd.DataFrame(overview_data)
            df_overview.to_excel(writer, sheet_name='项目概况', index=False)

            # 2. 科目分布
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT subject_name, COUNT(*) as cnt, SUM(amount) as total
                    FROM vouchers
                    WHERE project_id = ? AND subject_name IS NOT NULL
                    GROUP BY subject_name
                    ORDER BY total DESC
                    """,
                    [project_id]
                )
                subject_rows = cursor.fetchall()

            subject_data = []
            for row in subject_rows:
                subject_data.append({
                    "科目名称": row[0],
                    "凭证数量": row[1],
                    "金额合计": float(row[2])
                })

            df_subject = self.pd.DataFrame(subject_data)
            df_subject.to_excel(writer, sheet_name='科目分布', index=False)

            # 3. 抽样结果
            with get_db_cursor() as cursor:
                cursor.execute(
                    """
                    SELECT v.voucher_no, v.voucher_date, v.amount,
                           v.subject_name, v.description, s.risk_score, s.reason
                    FROM samples s
                    JOIN vouchers v ON s.voucher_id = v.id
                    WHERE s.project_id = ?
                    """,
                    [project_id]
                )
                sample_rows = cursor.fetchall()

            sample_data = []
            for row in sample_rows:
                sample_data.append({
                    "凭证编号": row[0],
                    "日期": str(row[1]) if row[1] else "",
                    "金额": float(row[2]) if row[2] else 0,
                    "科目": row[3] or "",
                    "摘要": row[4] or "",
                    "风险分": float(row[5]) if row[5] else "",
                    "抽取原因": row[6] or ""
                })

            df_samples = self.pd.DataFrame(sample_data)
            df_samples.to_excel(writer, sheet_name='抽样结果', index=False)

        output.seek(0)
        return output.getvalue()


class PDFExporter:
    """PDF导出器"""

    def __init__(self):
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.pdfbase import pdfmetrics
            from reportlab.pdfbase.ttfonts import TTFont

            self.colors = colors
            self.A4 = A4
            self.SimpleDocTemplate = SimpleDocTemplate
            self.Table = Table
            self.TableStyle = TableStyle
            self.Paragraph = Paragraph
            self.Spacer = Spacer
            self.getSampleStyleSheet = getSampleStyleSheet
            self.available = True

            # 尝试注册中文字体
            try:
                pdfmetrics.registerFont(TTFont('SimHei', 'simhei.ttf'))
                self.chinese_font = 'SimHei'
            except:
                self.chinese_font = None

        except ImportError:
            self.available = False

    def export_working_paper(
        self,
        project_id: str,
        title: str = "审计抽凭工作底稿"
    ) -> bytes:
        """
        导出工作底稿到PDF

        Args:
            project_id: 项目ID
            title: 底稿标题

        Returns:
            PDF文件字节
        """
        if not self.available:
            raise RuntimeError("请安装reportlab: pip install reportlab")

        output = io.BytesIO()

        doc = self.SimpleDocTemplate(output, pagesize=self.A4)
        elements = []

        # 样式
        styles = self.getSampleStyleSheet()
        if self.chinese_font:
            title_style = styles['Heading1']
            title_style.fontName = self.chinese_font

        # 标题
        elements.append(self.Paragraph(title, styles['Heading1']))
        elements.append(self.Spacer(1, 20))

        # 项目信息
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT name, description, created_at FROM projects WHERE id = ?",
                [project_id]
            )
            project = cursor.fetchone()

        if project:
            info_data = [
                ["项目名称", project[0]],
                ["项目描述", project[1] or ""],
                ["创建时间", str(project[2])]
            ]

            info_table = self.Table(info_data, colWidths=[100, 300])
            info_table.setStyle(self.TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), self.chinese_font or 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ]))
            elements.append(info_table)
            elements.append(self.Spacer(1, 20))

        # 抽凭汇总
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT COUNT(*) as total,
                       (SELECT COUNT(*) FROM vouchers WHERE project_id = ?) as population
                FROM samples
                WHERE project_id = ?
                """,
                [project_id, project_id]
            )
            stats = cursor.fetchone()

        summary_data = [
            ["凭证总体", str(stats[1])],
            ["抽样数量", str(stats[0])],
            ["抽样比例", f"{stats[0]/stats[1]*100:.1f}%" if stats[1] > 0 else "N/A"]
        ]

        summary_table = self.Table(summary_data, colWidths=[100, 100])
        summary_table.setStyle(self.TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), self.chinese_font or 'Helvetica'),
            ('GRID', (0, 0), (-1, -1), 1, self.colors.black),
        ]))
        elements.append(self.Paragraph("抽样概况", styles['Heading2']))
        elements.append(summary_table)

        # 构建PDF
        doc.build(elements)
        output.seek(0)

        return output.getvalue()


# 全局导出器实例
excel_exporter = ExcelExporter()
pdf_exporter = PDFExporter()


def save_export_file(
    file_data: bytes,
    filename: str,
    project_id: str = None
) -> str:
    """
    保存导出文件

    Args:
        file_data: 文件数据
        filename: 文件名
        project_id: 项目ID

    Returns:
        文件路径
    """
    # 创建导出目录
    export_dir = os.path.join(settings.PAPER_PATH, project_id or "")
    os.makedirs(export_dir, exist_ok=True)

    # 生成文件路径
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    full_filename = f"{timestamp}_{filename}"
    file_path = os.path.join(export_dir, full_filename)

    # 保存文件
    with open(file_path, 'wb') as f:
        f.write(file_data)

    return file_path