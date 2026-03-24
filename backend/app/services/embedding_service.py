"""
Embedding服务
用于凭证文本向量化，支持语义检索
"""
import json
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import asyncio

from collections import OrderedDict
from app.services.llm_service import LLMService, llm_service
from app.core.database import get_db_cursor


# Maximum cache size to prevent memory leaks
EMBEDDING_CACHE_MAX_SIZE = 1000


@dataclass
class EmbeddingResult:
    """向量化结果"""
    text: str
    embedding: List[float]
    model: str
    dimension: int


class EmbeddingService:
    """文本向量化服务"""

    def __init__(self, llm_service: LLMService = None):
        self.llm = llm_service or llm_service
        # Use OrderedDict for LRU cache
        self._embedding_cache: OrderedDict[str, List[float]] = OrderedDict()

    async def embed_text(self, text: str) -> EmbeddingResult:
        """
        单文本向量化

        Args:
            text: 输入文本

        Returns:
            EmbeddingResult: 向量化结果
        """
        # 检查缓存
        cache_key = self._get_cache_key(text)
        if cache_key in self._embedding_cache:
            return EmbeddingResult(
                text=text,
                embedding=self._embedding_cache[cache_key],
                model="cached",
                dimension=len(self._embedding_cache[cache_key])
            )

        # 调用LLM服务获取向量
        embedding = await self.llm.embed(text)

        # 缓存结果 (LRU eviction)
        self._embedding_cache[cache_key] = embedding
        if len(self._embedding_cache) > EMBEDDING_CACHE_MAX_SIZE:
            # Remove oldest entry
            self._embedding_cache.popitem(last=False)

        return EmbeddingResult(
            text=text,
            embedding=embedding,
            model=self.llm.config.model,
            dimension=len(embedding)
        )

    async def embed_batch(
        self,
        texts: List[str],
        batch_size: int = 10
    ) -> List[EmbeddingResult]:
        """
        批量文本向量化

        Args:
            texts: 文本列表
            batch_size: 批次大小

        Returns:
            List[EmbeddingResult]: 向量化结果列表
        """
        results = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            tasks = [self.embed_text(text) for text in batch]
            batch_results = await asyncio.gather(*tasks)
            results.extend(batch_results)

        return results

    def _get_cache_key(self, text: str) -> str:
        """生成缓存键"""
        import hashlib
        return hashlib.md5(text.encode()).hexdigest()

    def clear_cache(self):
        """清空缓存"""
        self._embedding_cache.clear()


class VectorStore:
    """向量存储（基于DuckDB的简单实现）"""

    def __init__(self):
        self._ensure_table()

    def _ensure_table(self):
        """确保向量表存在"""
        from app.core.database import get_db
        with get_db_cursor() as cursor:
            # 检查是否支持向量扩展
            try:
                cursor.execute("INSTALL vss;")
                cursor.execute("LOAD vss;")
            except:
                pass

            # 创建向量存储表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS voucher_embeddings (
                    id VARCHAR PRIMARY KEY,
                    voucher_id VARCHAR,
                    embedding BLOB,
                    text_content TEXT,
                    model VARCHAR,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_voucher_embeddings_voucher_id
                ON voucher_embeddings(voucher_id)
            """)

        get_db().commit()

    def store_embedding(
        self,
        voucher_id: str,
        embedding: List[float],
        text_content: str,
        model: str = "default"
    ) -> str:
        """
        存储向量

        Args:
            voucher_id: 凭证ID
            embedding: 向量
            text_content: 文本内容
            model: 模型名称

        Returns:
            str: 记录ID
        """
        import uuid

        record_id = str(uuid.uuid4())
        embedding_bytes = np.array(embedding, dtype=np.float32).tobytes()

        with get_db_cursor() as cursor:
            # 删除旧记录
            cursor.execute(
                "DELETE FROM voucher_embeddings WHERE voucher_id = ?",
                [voucher_id]
            )

            # 插入新记录
            cursor.execute(
                """
                INSERT INTO voucher_embeddings
                (id, voucher_id, embedding, text_content, model)
                VALUES (?, ?, ?, ?, ?)
                """,
                [record_id, voucher_id, embedding_bytes, text_content, model]
            )

            get_db().commit()

        return record_id

    def search_similar(
        self,
        query_embedding: List[float],
        project_id: str = None,
        top_k: int = 10,
        threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """
        搜索相似向量

        Args:
            query_embedding: 查询向量
            project_id: 项目ID（可选）
            top_k: 返回数量
            threshold: 相似度阈值

        Returns:
            List[Dict]: 相似结果列表
        """
        query_vec = np.array(query_embedding, dtype=np.float32)
        query_norm = np.linalg.norm(query_vec)

        if query_norm == 0:
            return []

        with get_db_cursor() as cursor:
            if project_id:
                cursor.execute(
                    """
                    SELECT e.id, e.voucher_id, e.embedding, e.text_content, e.model
                    FROM voucher_embeddings e
                    JOIN vouchers v ON e.voucher_id = v.id
                    WHERE v.project_id = ?
                    LIMIT 1000
                    """,
                    [project_id]
                )
            else:
                cursor.execute(
                    """
                    SELECT id, voucher_id, embedding, text_content, model
                    FROM voucher_embeddings
                    LIMIT 1000
                    """
                )

            rows = cursor.fetchall()

        results = []
        for row in rows:
            record_id, voucher_id, embedding_bytes, text_content, model = row

            # 解析向量
            vec = np.frombuffer(embedding_bytes, dtype=np.float32)
            vec_norm = np.linalg.norm(vec)

            if vec_norm == 0:
                continue

            # 计算余弦相似度
            similarity = np.dot(query_vec, vec) / (query_norm * vec_norm)

            if similarity >= threshold:
                results.append({
                    "id": record_id,
                    "voucher_id": voucher_id,
                    "text_content": text_content,
                    "similarity": float(similarity),
                    "model": model
                })

        # 按相似度排序
        results.sort(key=lambda x: x["similarity"], reverse=True)

        return results[:top_k]

    def delete_by_voucher(self, voucher_id: str):
        """删除指定凭证的向量"""
        with get_db_cursor() as cursor:
            cursor.execute(
                "DELETE FROM voucher_embeddings WHERE voucher_id = ?",
                [voucher_id]
            )
            get_db().commit()

    def delete_by_project(self, project_id: str):
        """删除指定项目的所有向量"""
        with get_db_cursor() as cursor:
            cursor.execute(
                """
                DELETE FROM voucher_embeddings
                WHERE voucher_id IN (
                    SELECT id FROM vouchers WHERE project_id = ?
                )
                """,
                [project_id]
            )
            get_db().commit()


class SemanticSearchService:
    """语义搜索服务"""

    def __init__(self, embedding_service: EmbeddingService = None):
        self.embedding = embedding_service or EmbeddingService()
        self.vector_store = VectorStore()

    async def index_voucher(
        self,
        voucher_id: str,
        text_content: str
    ) -> str:
        """
        为凭证建立语义索引

        Args:
            voucher_id: 凭证ID
            text_content: 文本内容（摘要+科目+交易对手等）

        Returns:
            str: 索引记录ID
        """
        # 向量化
        result = await self.embedding.embed_text(text_content)

        # 存储
        record_id = self.vector_store.store_embedding(
            voucher_id=voucher_id,
            embedding=result.embedding,
            text_content=text_content,
            model=result.model
        )

        return record_id

    async def batch_index_vouchers(
        self,
        vouchers: List[Dict[str, Any]]
    ) -> List[str]:
        """
        批量建立索引

        Args:
            vouchers: 凭证列表，每项包含id和text_content

        Returns:
            List[str]: 索引记录ID列表
        """
        record_ids = []

        for v in vouchers:
            text_content = self._build_text_content(v)
            record_id = await self.index_voucher(v["id"], text_content)
            record_ids.append(record_id)

        return record_ids

    def _build_text_content(self, voucher: Dict[str, Any]) -> str:
        """构建用于索引的文本内容"""
        parts = []

        if voucher.get("voucher_no"):
            parts.append(f"凭证号:{voucher['voucher_no']}")

        if voucher.get("subject_name"):
            parts.append(f"科目:{voucher['subject_name']}")

        if voucher.get("description"):
            parts.append(f"摘要:{voucher['description']}")

        if voucher.get("counterparty"):
            parts.append(f"交易对手:{voucher['counterparty']}")

        if voucher.get("amount"):
            parts.append(f"金额:{voucher['amount']}")

        return " ".join(parts)

    async def search(
        self,
        query: str,
        project_id: str = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        语义搜索

        Args:
            query: 查询文本
            project_id: 项目ID
            top_k: 返回数量

        Returns:
            List[Dict]: 搜索结果
        """
        # 查询向量化
        query_result = await self.embedding.embed_text(query)

        # 向量搜索
        results = self.vector_store.search_similar(
            query_embedding=query_result.embedding,
            project_id=project_id,
            top_k=top_k
        )

        # 获取凭证详情
        if results:
            voucher_ids = [r["voucher_id"] for r in results]
            voucher_details = self._get_voucher_details(voucher_ids)

            for r in results:
                r["voucher"] = voucher_details.get(r["voucher_id"], {})

        return results

    def _get_voucher_details(self, voucher_ids: List[str]) -> Dict[str, Dict]:
        """获取凭证详情"""
        with get_db_cursor() as cursor:
            placeholders = ",".join(["?" for _ in voucher_ids])
            cursor.execute(
                f"""
                SELECT id, voucher_no, voucher_date, amount,
                       subject_code, subject_name, description, counterparty
                FROM vouchers
                WHERE id IN ({placeholders})
                """,
                voucher_ids
            )
            rows = cursor.fetchall()

            return {
                row[0]: {
                    "id": row[0],
                    "voucher_no": row[1],
                    "voucher_date": str(row[2]) if row[2] else None,
                    "amount": float(row[3]) if row[3] else None,
                    "subject_code": row[4],
                    "subject_name": row[5],
                    "description": row[6],
                    "counterparty": row[7]
                }
                for row in rows
            }

    def delete_index(self, voucher_id: str):
        """删除凭证索引"""
        self.vector_store.delete_by_voucher(voucher_id)


# 全局服务实例
embedding_service = EmbeddingService()
semantic_search_service = SemanticSearchService()