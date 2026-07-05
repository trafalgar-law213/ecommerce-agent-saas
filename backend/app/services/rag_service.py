"""
RAG 知识库检索服务。

文档解析 → 文本分块 → 向量嵌入 → Chroma 存储 → 语义检索。
支持 PDF、DOCX、TXT 格式，使用 m3e-base 中文嵌入模型。
"""

import logging
import os
from pathlib import Path
from typing import Optional, List

_logger = logging.getLogger(__name__)

# 设置 HuggingFace 镜像（国内下载加速）
if not os.getenv("HF_ENDPOINT"):
    os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_chroma import Chroma

from ..config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, CHROMA_DIR

# ── 嵌入模型选择 ──────────────────────────────────────────────
# 使用 moka-ai/m3e-base：Moka AI 开源的中文嵌入模型（768 维向量）。
# 优先使用环境变量 M3E_MODEL_PATH 指定的本地模型路径，
# 如未设置则通过 HF_ENDPOINT 镜像下载（首次约 430MB）。

_EMBEDDING_MODEL = os.getenv(
    "M3E_MODEL_PATH",
    "moka-ai/m3e-base",
).strip()

# ── 分块参数 ──────────────────────────────────────────────────
_CHUNK_SIZE = 500      # 每个文本块的最大字符数
_CHUNK_OVERLAP = 50    # 相邻块之间的重叠字符数


class RAGService:
    """RAG 知识库服务。

    封装文档解析、向量存储和语义检索。整个应用共用单例实例。
    """

    def __init__(self):
        self._embeddings: Optional[HuggingFaceEmbeddings] = None
        self._vectorstore: Optional[Chroma] = None
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=_CHUNK_SIZE,
            chunk_overlap=_CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""],
        )

    # ── 延迟初始化（避免模块导入时就加载模型）─────────────────

    @property
    def embeddings(self) -> HuggingFaceEmbeddings:
        """延迟初始化嵌入模型。"""
        if self._embeddings is None:
            self._embeddings = HuggingFaceEmbeddings(
                model_name=_EMBEDDING_MODEL,
                model_kwargs={"device": "cpu"},
                encode_kwargs={"normalize_embeddings": True},
            )
        return self._embeddings

    @property
    def vectorstore(self) -> Chroma:
        """延迟初始化 Chroma 向量存储。"""
        if self._vectorstore is None:
            self._vectorstore = Chroma(
                collection_name="knowledge_base",
                embedding_function=self.embeddings,
                persist_directory=str(CHROMA_DIR),
            )
        return self._vectorstore

    # ── 文档摄取 ───────────────────────────────────────────────

    def ingest_document(self, file_path: Path, filename: str) -> dict:
        """解析文档、分块、向量化并存入 Chroma。

        Args:
            file_path: 文档文件路径
            filename: 原始文件名（用于来源标注）

        Returns:
            {"status": "ok", "chunks": 分块数量, "filename": 文件名}
        """
        # 1. 根据文件类型选择加载器
        suffix = file_path.suffix.lower()
        if suffix == ".pdf":
            loader = PyPDFLoader(str(file_path))
        elif suffix == ".docx":
            loader = Docx2txtLoader(str(file_path))
        elif suffix == ".txt":
            loader = TextLoader(str(file_path), encoding="utf-8")
        else:
            raise ValueError(f"不支持的文件格式：{suffix}。支持的格式：PDF、DOCX、TXT")

        # 2. 加载文档
        documents = loader.load()
        if not documents:
            raise ValueError("文档内容为空，无法处理")

        # 3. 文本分块
        chunks = self._splitter.split_documents(documents)

        # 4. 为每个分块添加来源元数据
        for i, chunk in enumerate(chunks):
            chunk.metadata["source"] = filename
            chunk.metadata["chunk_index"] = i

        # 5. 存入 Chroma 向量库
        self.vectorstore.add_documents(chunks)

        return {
            "status": "ok",
            "chunks": len(chunks),
            "filename": filename,
        }

    # ── 语义检索 ───────────────────────────────────────────────

    def search(self, query: str, top_k: int = 5) -> List[dict]:
        """在知识库中检索与查询最相关的文档片段。

        Args:
            query: 用户查询文本
            top_k: 返回的最相关结果数量

        Returns:
            [{"content": "片段文本", "source": "来源文件名", "score": 相似度分数}, ...]
        """
        docs = self.vectorstore.similarity_search_with_score(query, k=top_k)

        results = []
        for doc, score in docs:
            results.append({
                "content": doc.page_content,
                "source": doc.metadata.get("source", "未知文档"),
                "score": round(float(score), 4),
            })

        return results

    # ── 知识库管理 ─────────────────────────────────────────────

    def get_document_count(self) -> int:
        """获取知识库中已索引的文档分块总数。"""
        try:
            collection = self.vectorstore._collection
            return collection.count()
        except Exception as e:
            _logger.error(f"获取文档数量失败：{e}", exc_info=True)
            return 0

    def get_document_sources(self) -> List[str]:
        """获取知识库中所有唯一的文档来源名称。"""
        try:
            collection = self.vectorstore._collection
            result = collection.get()
            sources = set()
            for metadata in (result.get("metadatas") or []):
                src = metadata.get("source", "")
                if src:
                    sources.add(src)
            return sorted(sources)
        except Exception as e:
            _logger.error(f"获取文档来源列表失败：{e}", exc_info=True)
            return []

    def delete_document(self, filename: str) -> bool:
        """从知识库中删除指定文档的所有分块。

        Args:
            filename: 要删除的文档文件名

        Returns:
            True 表示删除成功，False 表示未找到
        """
        try:
            collection = self.vectorstore._collection
            # Chroma 按 metadata 过滤删除
            collection.delete(where={"source": filename})
            _logger.info(f"已从知识库删除文档：{filename}")
            return True
        except Exception as e:
            _logger.error(f"删除文档失败（{filename}）：{e}", exc_info=True)
            return False


# ── 全局单例 ───────────────────────────────────────────────────

rag_service = RAGService()
