"""
工作底稿生成服务
自动汇总抽样结果、差异说明、替代测试结论，生成结构化工作底稿
"""
import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, date
from enum import Enum
import uuid

from app.core.database import get_db_cursor, get_db


class PaperType(str, Enum):
    """底稿类型"""
    SAMPLING_SUMMARY = "sampling_summary"      # 抽样汇总
    SUBSTANTIVE_TEST = "substantive_test"      # 实质性测试
    COMPLIANCE_TEST = "compliance_test"        # 合规性测试
    RISK_ASSESSMENT = "risk_assessment"        # 风险评估
    THREE_WAY_MATCH = "three_way_match"        # 三单匹配
    AUDIT_ADJUSTMENT = "audit_adjustment"      # 审计调整
    MANAGEMENT_LETTER = "management_letter"    # 管理建议书


@dataclass
class PaperSection:
    """底稿章节"""
    title: str
    content: str
    order: int
    data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class WorkingPaper:
    """工作底稿"""
    id: str
    project_id: str
    paper_type: PaperType
    title: str
    sections: List[PaperSection]
    ai_description: str
    status: str
    version: int
    created_at: datetime
    updated_at: datetime


@dataclass
class SamplingSummaryData:
    """抽样汇总数据"""
    total_population: int
    sample_size: int
    sampling_rate: float
    sampling_method: str
    confidence_level: float
    subject_breakdown: Dict[str, int]
    risk_distribution: Dict[str, int]


@dataclass
class DifferenceAnalysisData:
    """差异分析数据"""
    total_differences: int
    by_type: Dict[str, int]
    by_severity: Dict[str, int]
    details: List[Dict[str, Any]]


class WorkingPaperGenerator:
    """工作底稿生成器"""

    def __init__(self):
        self.templates = self._load_templates()

    def _load_templates(self) -> Dict[PaperType, Dict[str, Any]]:
        """加载底稿模板"""
        return {
            PaperType.SAMPLING_SUMMARY: {
                "title": "抽样情况汇总表",
                "sections": [
                    {"title": "一、项目概述", "order": 1},
                    {"title": "二、抽样方法说明", "order": 2},
                    {"title": "三、样本量计算", "order": 3},
                    {"title": "四、抽样结果汇总", "order": 4},
                    {"title": "五、风险分布统计", "order": 5},
                    {"title": "六、审计说明", "order": 6}
                ]
            },
            PaperType.SUBSTANTIVE_TEST: {
                "title": "实质性程序测试底稿",
                "sections": [
                    {"title": "一、测试目标", "order": 1},
                    {"title": "二、测试程序", "order": 2},
                    {"title": "三、样本选取", "order": 3},
                    {"title": "四、测试过程", "order": 4},
                    {"title": "五、测试结论", "order": 5},
                    {"title": "六、发现问题", "order": 6}
                ]
            },
            PaperType.THREE_WAY_MATCH: {
                "title": "三单匹配核对底稿",
                "sections": [
                    {"title": "一、核对范围", "order": 1},
                    {"title": "二、匹配结果汇总", "order": 2},
                    {"title": "三、差异分析", "order": 3},
                    {"title": "四、问题跟进", "order": 4},
                    {"title": "五、结论", "order": 5}
                ]
            },
            PaperType.RISK_ASSESSMENT: {
                "title": "风险评估底稿",
                "sections": [
                    {"title": "一、风险评估方法", "order": 1},
                    {"title": "二、风险识别结果", "order": 2},
                    {"title": "三、风险等级分布", "order": 3},
                    {"title": "四、重点关注事项", "order": 4},
                    {"title": "五、应对措施", "order": 5}
                ]
            }
        }

    def generate_sampling_summary(
        self,
        project_id: str,
        include_ai_description: bool = True
    ) -> WorkingPaper:
        """
        生成抽样汇总底稿

        Args:
            project_id: 项目ID
            include_ai_description: 是否包含AI生成的描述

        Returns:
            WorkingPaper: 生成的底稿
        """
        # 收集数据
        project_info = self._get_project_info(project_id)
        sampling_data = self._get_sampling_summary(project_id)
        subject_breakdown = self._get_subject_breakdown(project_id)
        risk_distribution = self._get_risk_distribution(project_id)

        # 生成章节
        sections = []

        # 一、项目概述
        sections.append(PaperSection(
            title="一、项目概述",
            content=self._generate_project_overview(project_info),
            order=1,
            data=project_info
        ))

        # 二、抽样方法说明
        sections.append(PaperSection(
            title="二、抽样方法说明",
            content=self._generate_sampling_method_description(sampling_data),
            order=2,
            data={"method": sampling_data.get("sampling_method", "随机抽样")}
        ))

        # 三、样本量计算
        sections.append(PaperSection(
            title="三、样本量计算",
            content=self._generate_sample_size_calculation(sampling_data),
            order=3,
            data={
                "population": sampling_data.get("total_population", 0),
                "sample_size": sampling_data.get("sample_size", 0),
                "confidence_level": sampling_data.get("confidence_level", 0.95)
            }
        ))

        # 四、抽样结果汇总
        sections.append(PaperSection(
            title="四、抽样结果汇总",
            content=self._generate_sampling_results_table(project_id),
            order=4,
            data=subject_breakdown
        ))

        # 五、风险分布统计
        sections.append(PaperSection(
            title="五、风险分布统计",
            content=self._generate_risk_distribution_table(risk_distribution),
            order=5,
            data=risk_distribution
        ))

        # 六、审计说明
        ai_description = ""
        if include_ai_description:
            ai_description = self._generate_ai_description(project_id, sampling_data, risk_distribution)

        sections.append(PaperSection(
            title="六、审计说明",
            content=ai_description,
            order=6,
            data={}
        ))

        # 创建底稿
        paper = WorkingPaper(
            id=str(uuid.uuid4()),
            project_id=project_id,
            paper_type=PaperType.SAMPLING_SUMMARY,
            title=f"抽样情况汇总表 - {project_info.get('name', '未知项目')}",
            sections=sections,
            ai_description=ai_description,
            status="draft",
            version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        # 保存底稿
        self._save_paper(paper)

        return paper

    def generate_substantive_test(
        self,
        project_id: str,
        subject_code: str,
        test_procedures: List[str] = None
    ) -> WorkingPaper:
        """
        生成实质性测试底稿

        Args:
            project_id: 项目ID
            subject_code: 科目代码
            test_procedures: 测试程序列表

        Returns:
            WorkingPaper: 生成的底稿
        """
        sections = []

        # 一、测试目标
        sections.append(PaperSection(
            title="一、测试目标",
            content=f"验证{subject_code}科目的真实性、完整性和准确性。",
            order=1,
            data={"subject_code": subject_code}
        ))

        # 二、测试程序
        default_procedures = [
            "1. 抽取一定数量的凭证，核对原始单据",
            "2. 检查大额和异常交易",
            "3. 执行截止测试",
            "4. 函证重要交易对手",
            "5. 分析性复核"
        ]
        procedures = test_procedures or default_procedures

        sections.append(PaperSection(
            title="二、测试程序",
            content="\n".join(procedures),
            order=2,
            data={"procedures": procedures}
        ))

        # 三、样本选取
        samples = self._get_subject_samples(project_id, subject_code)
        sections.append(PaperSection(
            title="三、样本选取",
            content=self._generate_sample_selection_table(samples),
            order=3,
            data={"sample_count": len(samples)}
        ))

        # 四、测试过程
        sections.append(PaperSection(
            title="四、测试过程",
            content=self._generate_test_process_description(samples),
            order=4,
            data={}
        ))

        # 五、测试结论
        conclusions = self._generate_test_conclusions(project_id, subject_code, samples)
        sections.append(PaperSection(
            title="五、测试结论",
            content=conclusions,
            order=5,
            data={}
        ))

        # 六、发现问题
        issues = self._get_subject_issues(project_id, subject_code)
        sections.append(PaperSection(
            title="六、发现问题",
            content=self._generate_issues_description(issues),
            order=6,
            data={"issues": issues}
        ))

        project_info = self._get_project_info(project_id)

        paper = WorkingPaper(
            id=str(uuid.uuid4()),
            project_id=project_id,
            paper_type=PaperType.SUBSTANTIVE_TEST,
            title=f"实质性程序测试底稿 - {subject_code}",
            sections=sections,
            ai_description="",
            status="draft",
            version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        self._save_paper(paper)

        return paper

    def generate_three_way_match_paper(
        self,
        project_id: str,
        match_results: List[Dict[str, Any]]
    ) -> WorkingPaper:
        """
        生成三单匹配底稿

        Args:
            project_id: 项目ID
            match_results: 匹配结果列表

        Returns:
            WorkingPaper: 生成的底稿
        """
        sections = []

        # 统计匹配结果
        matched_count = len([r for r in match_results if r.get("match_status") == "fully_matched"])
        partial_count = len([r for r in match_results if r.get("match_status") == "partially_matched"])
        not_matched_count = len([r for r in match_results if r.get("match_status") == "not_matched"])

        # 一、核对范围
        sections.append(PaperSection(
            title="一、核对范围",
            content=f"本次核对共涉及{len(match_results)}笔采购业务，包括发票、采购订单和入库单的三单匹配。",
            order=1,
            data={"total": len(match_results)}
        ))

        # 二、匹配结果汇总
        summary_content = f"""
| 匹配状态 | 数量 | 占比 |
|---------|------|------|
| 完全匹配 | {matched_count} | {matched_count/len(match_results)*100:.1f}% |
| 部分匹配 | {partial_count} | {partial_count/len(match_results)*100:.1f}% |
| 未匹配 | {not_matched_count} | {not_matched_count/len(match_results)*100:.1f}% |
"""
        sections.append(PaperSection(
            title="二、匹配结果汇总",
            content=summary_content,
            order=2,
            data={
                "matched": matched_count,
                "partial": partial_count,
                "not_matched": not_matched_count
            }
        ))

        # 三、差异分析
        differences = [r for r in match_results if r.get("differences")]
        sections.append(PaperSection(
            title="三、差异分析",
            content=self._generate_difference_analysis(differences),
            order=3,
            data={"differences_count": len(differences)}
        ))

        # 四、问题跟进
        sections.append(PaperSection(
            title="四、问题跟进",
            content=self._generate_follow_up_items(differences),
            order=4,
            data={}
        ))

        # 五、结论
        conclusions = "经核对，三单匹配整体情况"
        if matched_count / len(match_results) > 0.9:
            conclusions += "良好，大部分交易匹配一致。"
        elif matched_count / len(match_results) > 0.7:
            conclusions += "一般，存在部分差异需关注。"
        else:
            conclusions += "较差，存在较多差异需重点核查。"

        sections.append(PaperSection(
            title="五、结论",
            content=conclusions,
            order=5,
            data={}
        ))

        project_info = self._get_project_info(project_id)

        paper = WorkingPaper(
            id=str(uuid.uuid4()),
            project_id=project_id,
            paper_type=PaperType.THREE_WAY_MATCH,
            title=f"三单匹配核对底稿",
            sections=sections,
            ai_description="",
            status="draft",
            version=1,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )

        self._save_paper(paper)

        return paper

    def _get_project_info(self, project_id: str) -> Dict[str, Any]:
        """获取项目信息"""
        with get_db_cursor() as cursor:
            cursor.execute(
                "SELECT id, name, description, status, created_at FROM projects WHERE id = ?",
                [project_id]
            )
            row = cursor.fetchone()

            if not row:
                return {}

            return {
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "status": row[3],
                "created_at": str(row[4])
            }

    def _get_sampling_summary(self, project_id: str) -> Dict[str, Any]:
        """获取抽样汇总数据"""
        with get_db_cursor() as cursor:
            # 总体数量
            cursor.execute(
                "SELECT COUNT(*) FROM vouchers WHERE project_id = ?",
                [project_id]
            )
            total_population = cursor.fetchone()[0] or 0

            # 样本数量
            cursor.execute(
                "SELECT COUNT(*) FROM samples WHERE project_id = ?",
                [project_id]
            )
            sample_size = cursor.fetchone()[0] or 0

            # 规则类型
            cursor.execute(
                """
                SELECT DISTINCT sr.rule_type
                FROM samples s
                JOIN sampling_rules sr ON s.rule_id = sr.id
                WHERE s.project_id = ?
                """,
                [project_id]
            )
            rule_types = [row[0] for row in cursor.fetchall()]

        sampling_rate = sample_size / total_population if total_population > 0 else 0

        return {
            "total_population": total_population,
            "sample_size": sample_size,
            "sampling_rate": sampling_rate,
            "sampling_method": ", ".join(rule_types) if rule_types else "随机抽样",
            "confidence_level": 0.95
        }

    def _get_subject_breakdown(self, project_id: str) -> Dict[str, int]:
        """获取科目分布"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT v.subject_name, COUNT(*) as cnt
                FROM samples s
                JOIN vouchers v ON s.voucher_id = v.id
                WHERE s.project_id = ?
                GROUP BY v.subject_name
                ORDER BY cnt DESC
                """,
                [project_id]
            )
            return {row[0] or "未分类": row[1] for row in cursor.fetchall()}

    def _get_risk_distribution(self, project_id: str) -> Dict[str, int]:
        """获取风险分布"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT vc.risk_tag, COUNT(*) as cnt
                FROM voucher_categories vc
                JOIN vouchers v ON vc.voucher_id = v.id
                WHERE v.project_id = ?
                GROUP BY vc.risk_tag
                """,
                [project_id]
            )
            return {row[0] or "normal": row[1] for row in cursor.fetchall()}

    def _generate_project_overview(self, project_info: Dict[str, Any]) -> str:
        """生成项目概述"""
        return f"""
项目名称：{project_info.get('name', '未知')}
项目状态：{project_info.get('status', '进行中')}
创建时间：{project_info.get('created_at', '')}

{project_info.get('description', '')}
"""

    def _generate_sampling_method_description(self, sampling_data: Dict[str, Any]) -> str:
        """生成抽样方法说明"""
        method = sampling_data.get("sampling_method", "随机抽样")
        rate = sampling_data.get("sampling_rate", 0) * 100

        return f"""
本次审计抽样采用{method}方法，抽样比例为{rate:.1f}%。

抽样依据：
1. 根据风险评估结果确定抽样重点
2. 结合重要性水平确定样本量
3. 综合考虑审计资源和时间限制
"""

    def _generate_sample_size_calculation(self, sampling_data: Dict[str, Any]) -> str:
        """生成样本量计算说明"""
        population = sampling_data.get("total_population", 0)
        sample_size = sampling_data.get("sample_size", 0)
        confidence = sampling_data.get("confidence_level", 0.95) * 100

        return f"""
总体规模：{population}笔
样本量：{sample_size}笔
置信水平：{confidence:.0f}%

样本量计算公式：n = (Z² × p × (1-p)) / e²
其中：Z为置信水平对应的z值，p为预期偏差率，e为可容忍误差
"""

    def _generate_sampling_results_table(self, project_id: str) -> str:
        """生成抽样结果表格"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT v.voucher_no, v.voucher_date, v.amount, v.subject_name, v.description
                FROM samples s
                JOIN vouchers v ON s.voucher_id = v.id
                WHERE s.project_id = ?
                ORDER BY v.voucher_date
                LIMIT 50
                """,
                [project_id]
            )
            rows = cursor.fetchall()

        if not rows:
            return "暂无抽样数据"

        lines = ["| 凭证号 | 日期 | 金额 | 科目 | 摘要 |", "|--------|------|------|------|------|"]
        for row in rows:
            lines.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3] or ''} | {(row[4] or '')[:20]} |")

        return "\n".join(lines)

    def _generate_risk_distribution_table(self, risk_distribution: Dict[str, int]) -> str:
        """生成风险分布表格"""
        total = sum(risk_distribution.values()) or 1

        lines = ["| 风险等级 | 数量 | 占比 |", "|----------|------|------|"]
        for level, count in risk_distribution.items():
            lines.append(f"| {level} | {count} | {count/total*100:.1f}% |")

        return "\n".join(lines)

    def _generate_ai_description(
        self,
        project_id: str,
        sampling_data: Dict[str, Any],
        risk_distribution: Dict[str, int]
    ) -> str:
        """生成AI审计说明"""
        population = sampling_data.get("total_population", 0)
        sample_size = sampling_data.get("sample_size", 0)
        rate = sampling_data.get("sampling_rate", 0) * 100

        high_risk = risk_distribution.get("high_risk", 0)
        anomaly = risk_distribution.get("anomaly", 0)

        description = f"""
【AI自动生成】

本次审计共抽取{sample_size}个样本，占总体{population}笔凭证的{rate:.1f}%。

风险分析结果：
- 高风险凭证：{high_risk}笔
- 异常凭证：{anomaly}笔

审计建议：
1. 对高风险凭证进行重点审查
2. 核实异常凭证的业务背景
3. 关注大额交易的审批流程
4. 检查跨期调整的合理性

结论：
本次抽样符合审计准则要求，样本具有代表性。建议按照审计程序完成后续工作。
"""
        return description.strip()

    def _get_subject_samples(self, project_id: str, subject_code: str) -> List[Dict[str, Any]]:
        """获取科目样本"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT v.id, v.voucher_no, v.voucher_date, v.amount, v.description
                FROM samples s
                JOIN vouchers v ON s.voucher_id = v.id
                WHERE s.project_id = ? AND v.subject_code LIKE ?
                """,
                [project_id, f"{subject_code}%"]
            )
            return [
                {
                    "id": row[0],
                    "voucher_no": row[1],
                    "voucher_date": str(row[2]) if row[2] else "",
                    "amount": float(row[3]) if row[3] else 0,
                    "description": row[4]
                }
                for row in cursor.fetchall()
            ]

    def _generate_sample_selection_table(self, samples: List[Dict[str, Any]]) -> str:
        """生成样本选取表格"""
        if not samples:
            return "暂无样本"

        lines = ["| 序号 | 凭证号 | 日期 | 金额 |", "|------|--------|------|------|"]
        for i, s in enumerate(samples[:20], 1):
            lines.append(f"| {i} | {s['voucher_no']} | {s['voucher_date']} | {s['amount']:,.2f} |")

        return "\n".join(lines)

    def _generate_test_process_description(self, samples: List[Dict[str, Any]]) -> str:
        """生成测试过程描述"""
        return f"""
测试过程：

1. 凭证检查：检查{len(samples)}份凭证的完整性
2. 原始单据核对：核对发票、合同等原始单据
3. 金额计算验证：验证金额计算准确性
4. 授权审批检查：检查审批流程合规性
5. 截止测试：检查跨期调整合理性
"""

    def _generate_test_conclusions(
        self,
        project_id: str,
        subject_code: str,
        samples: List[Dict[str, Any]]
    ) -> str:
        """生成测试结论"""
        return f"""
测试结论：

经对{subject_code}科目执行实质性程序，总体情况良好。

1. 真实性：样本凭证均附有原始单据支持
2. 完整性：交易记录完整，未发现遗漏
3. 准确性：金额计算准确，未发现重大差错
4. 截止：交易记录期间正确
"""

    def _get_subject_issues(self, project_id: str, subject_code: str) -> List[Dict[str, Any]]:
        """获取科目问题"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT ca.rule_name, ca.alert_message, ca.severity
                FROM compliance_alerts ca
                JOIN vouchers v ON ca.voucher_id = v.id
                WHERE v.project_id = ? AND v.subject_code LIKE ?
                ORDER BY ca.created_at DESC
                """,
                [project_id, f"{subject_code}%"]
            )
            return [
                {
                    "rule": row[0],
                    "message": row[1],
                    "severity": row[2]
                }
                for row in cursor.fetchall()
            ]

    def _generate_issues_description(self, issues: List[Dict[str, Any]]) -> str:
        """生成问题描述"""
        if not issues:
            return "本次测试未发现重大问题。"

        lines = ["| 问题类型 | 描述 | 严重程度 |", "|----------|------|----------|"]
        for issue in issues[:10]:
            lines.append(f"| {issue['rule']} | {issue['message'][:50]} | {issue['severity']} |")

        return "\n".join(lines)

    def _generate_difference_analysis(self, differences: List[Dict[str, Any]]) -> str:
        """生成差异分析"""
        if not differences:
            return "未发现差异。"

        lines = ["| 凭证号 | 差异类型 | 差异说明 |", "|--------|----------|----------|"]
        for diff in differences[:10]:
            voucher_no = diff.get("invoice_no", "")
            diff_desc = diff.get("differences", [])
            desc_str = json.dumps(diff_desc, ensure_ascii=False)[:50] if diff_desc else ""
            lines.append(f"| {voucher_no} | {diff.get('match_status', '')} | {desc_str} |")

        return "\n".join(lines)

    def _generate_follow_up_items(self, differences: List[Dict[str, Any]]) -> str:
        """生成跟进事项"""
        if not differences:
            return "无需跟进事项。"

        items = []
        for i, diff in enumerate(differences[:5], 1):
            items.append(f"{i}. {diff.get('invoice_no', '')}: {', '.join(diff.get('suggestions', ['待核实']))}")

        return "\n".join(items)

    def _save_paper(self, paper: WorkingPaper):
        """保存底稿"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO working_papers
                (id, project_id, paper_type, title, content, ai_description, generated_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    paper.id,
                    paper.project_id,
                    paper.paper_type.value,
                    paper.title,
                    json.dumps([{
                        "title": s.title,
                        "content": s.content,
                        "order": s.order,
                        "data": s.data
                    } for s in paper.sections], ensure_ascii=False),
                    paper.ai_description,
                    paper.created_at,
                    paper.updated_at
                ]
            )
            get_db().commit()

    def get_paper(self, paper_id: str) -> Optional[WorkingPaper]:
        """获取底稿"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, project_id, paper_type, title, content, ai_description, generated_at, updated_at
                FROM working_papers
                WHERE id = ?
                """,
                [paper_id]
            )
            row = cursor.fetchone()

            if not row:
                return None

            content = json.loads(row[4]) if isinstance(row[4], str) else row[4]
            sections = [
                PaperSection(
                    title=s.get("title", ""),
                    content=s.get("content", ""),
                    order=s.get("order", 0),
                    data=s.get("data", {})
                )
                for s in content
            ]

            return WorkingPaper(
                id=row[0],
                project_id=row[1],
                paper_type=PaperType(row[2]),
                title=row[3],
                sections=sections,
                ai_description=row[5] or "",
                status="draft",
                version=1,
                created_at=row[6],
                updated_at=row[7]
            )

    def get_project_papers(self, project_id: str) -> List[WorkingPaper]:
        """获取项目底稿列表"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                SELECT id, project_id, paper_type, title, content, ai_description, generated_at, updated_at
                FROM working_papers
                WHERE project_id = ?
                ORDER BY generated_at DESC
                """,
                [project_id]
            )
            rows = cursor.fetchall()

            papers = []
            for row in rows:
                content = json.loads(row[4]) if isinstance(row[4], str) else row[4]
                sections = [
                    PaperSection(
                        title=s.get("title", ""),
                        content=s.get("content", ""),
                        order=s.get("order", 0),
                        data=s.get("data", {})
                    )
                    for s in content
                ]

                papers.append(WorkingPaper(
                    id=row[0],
                    project_id=row[1],
                    paper_type=PaperType(row[2]),
                    title=row[3],
                    sections=sections,
                    ai_description=row[5] or "",
                    status="draft",
                    version=1,
                    created_at=row[6],
                    updated_at=row[7]
                ))

            return papers

    def update_paper(self, paper: WorkingPaper):
        """更新底稿"""
        paper.updated_at = datetime.now()

        with get_db_cursor() as cursor:
            cursor.execute(
                """
                UPDATE working_papers
                SET title = ?, content = ?, ai_description = ?, updated_at = ?
                WHERE id = ?
                """,
                [
                    paper.title,
                    json.dumps([{
                        "title": s.title,
                        "content": s.content,
                        "order": s.order,
                        "data": s.data
                    } for s in paper.sections], ensure_ascii=False),
                    paper.ai_description,
                    paper.updated_at,
                    paper.id
                ]
            )
            get_db().commit()

    def delete_paper(self, paper_id: str):
        """删除底稿"""
        with get_db_cursor() as cursor:
            cursor.execute("DELETE FROM working_papers WHERE id = ?", [paper_id])
            get_db().commit()


# 全局服务实例
working_paper_generator = WorkingPaperGenerator()