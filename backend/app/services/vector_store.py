import os
import json
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.core.config import settings

# ========================================================================
# FAISS 可用性检测：若导入失败则自动降级到 numpy 实现
# ========================================================================
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("[VectorStore] 警告: faiss 未安装，已自动降级到 numpy 实现")


def _l2_normalize(vec: np.ndarray) -> np.ndarray:
    """对向量进行 L2 归一化（归一化后内积等价于余弦相似度）"""
    norm = np.linalg.norm(vec)
    if norm == 0:
        return vec
    return vec / norm


# ========================================================================
# VectorStore —— 对外接口完全兼容旧版本，内部优先使用 FAISS
# ========================================================================
class VectorStore:
    """基于 FAISS(IndexFlatIP) 的向量存储，保持与旧版 JSON+numpy 接口兼容"""

    # ------------------------------------------------------------------
    # 初始化
    # ------------------------------------------------------------------
    def __init__(self):
        self.db_path = os.path.join(settings.VECTOR_DB_PATH, "vector_data.json")
        self.index_path = os.path.join(settings.VECTOR_DB_PATH, "faiss.index")

        # 所有模式共享的数据结构（与旧格式一致）
        self._vectors: Dict[str, List[float]] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}

        if FAISS_AVAILABLE:
            self._faiss_index: Optional[Any] = None       # faiss.IndexFlatIP
            self._id_to_index: Dict[str, int] = {}        # vector_id -> 当前FAISS行号
            self._index_to_id: Dict[int, str] = {}        # FAISS行号 -> vector_id
            self._dim: Optional[int] = None
            self._load_faiss()
        else:
            self._load()

    # ==================================================================
    # 持久化：JSON（向量 + 元数据）+ FAISS 索引文件
    # ==================================================================

    def _load(self):
        """numpy 降级模式：从 JSON 加载向量数据"""
        os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._vectors = data.get("vectors", {})
                    self._metadata = data.get("metadata", {})
            except Exception as e:
                print(f"[VectorStore] 加载向量数据库失败: {e}")
                self._vectors = {}
                self._metadata = {}

    def _save(self):
        """保存向量 + 元数据到 JSON（格式与旧版一致，向后兼容）"""
        os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)
        data = {
            "vectors": self._vectors,
            "metadata": self._metadata,
            "updated_at": datetime.utcnow().isoformat(),
        }
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _save_faiss(self):
        """保存 FAISS 索引到磁盘"""
        if self._faiss_index is not None:
            os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)
            faiss.write_index(self._faiss_index, self.index_path)

    # ------------------------------------------------------------------
    # FAISS 加载 / 迁移
    # ------------------------------------------------------------------
    def _load_faiss(self):
        """加载 FAISS 索引与 JSON 元数据，必要时自动迁移"""
        os.makedirs(settings.VECTOR_DB_PATH, exist_ok=True)

        json_exists = os.path.exists(self.db_path)
        index_exists = os.path.exists(self.index_path)

        # 1) 加载 JSON 元数据（向量 + metadata）
        if json_exists:
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self._vectors = data.get("vectors", {})
                    self._metadata = data.get("metadata", {})
            except Exception as e:
                print(f"[VectorStore] 加载 JSON 元数据失败: {e}")
                self._vectors = {}
                self._metadata = {}

        # 空库
        if not self._vectors:
            self._faiss_index = None
            self._id_to_index = {}
            self._index_to_id = {}
            self._dim = None
            return

        self._dim = len(next(iter(self._vectors.values())))

        # 2) 加载或重建 FAISS 索引
        if index_exists:
            try:
                self._faiss_index = faiss.read_index(self.index_path)
                self._rebuild_id_mappings()
                # 一致性校验：索引大小与活跃向量数一致才视为有效
                if self._faiss_index.ntotal != len(self._vectors):
                    print(
                        f"[VectorStore] FAISS 索引大小({self._faiss_index.ntotal})"
                        f"与 JSON 数据量({len(self._vectors)})不一致，自动重建"
                    )
                    self._rebuild_index()
            except Exception as e:
                print(f"[VectorStore] 加载 FAISS 索引失败: {e}，将从 JSON 重建")
                self._migrate_from_json()
        else:
            # 首次启动：旧 JSON 存在但 faiss.index 不存在 → 自动迁移
            self._migrate_from_json()

    def _migrate_from_json(self):
        """从旧版 JSON 数据自动构建 FAISS 索引（首次启动迁移）"""
        print("[VectorStore] 检测到旧版 JSON 向量数据，正在自动迁移到 FAISS ...")
        if not self._vectors:
            self._faiss_index = None
            return

        self._dim = len(next(iter(self._vectors.values())))
        self._faiss_index = faiss.IndexFlatIP(self._dim)
        self._id_to_index = {}
        self._index_to_id = {}

        vec_list = []
        for vid, emb in self._vectors.items():
            v = np.array(emb, dtype=np.float32)
            v = _l2_normalize(v)
            vec_list.append(v)

        if vec_list:
            matrix = np.array(vec_list, dtype=np.float32)
            self._faiss_index.add(matrix)
            for i, vid in enumerate(self._vectors.keys()):
                self._id_to_index[vid] = i
                self._index_to_id[i] = vid

        self._save_faiss()
        print(f"[VectorStore] 迁移完成，共 {self._faiss_index.ntotal} 个向量")

    def _rebuild_id_mappings(self):
        """基于当前 _vectors 的插入顺序重建 id <-> index 映射"""
        self._id_to_index = {}
        self._index_to_id = {}
        for i, vid in enumerate(self._vectors.keys()):
            self._id_to_index[vid] = i
            self._index_to_id[i] = vid

    def _rebuild_index(self):
        """重建 FAISS 索引（清除已删除/替换产生的陈旧条目，压缩索引体积）"""
        if not self._vectors:
            self._faiss_index = (
                faiss.IndexFlatIP(self._dim) if self._dim is not None else None
            )
            self._id_to_index = {}
            self._index_to_id = {}
            self._save_faiss()
            return

        self._dim = len(next(iter(self._vectors.values())))
        new_index = faiss.IndexFlatIP(self._dim)

        active_ids = list(self._vectors.keys())
        vec_list = []
        for vid in active_ids:
            v = np.array(self._vectors[vid], dtype=np.float32)
            v = _l2_normalize(v)
            vec_list.append(v)

        if vec_list:
            matrix = np.array(vec_list, dtype=np.float32)
            new_index.add(matrix)

        new_id_to_index: Dict[str, int] = {}
        new_index_to_id: Dict[int, str] = {}
        for i, vid in enumerate(active_ids):
            new_id_to_index[vid] = i
            new_index_to_id[i] = vid

        self._faiss_index = new_index
        self._id_to_index = new_id_to_index
        self._index_to_id = new_index_to_id
        self._save_faiss()

    def _maybe_rebuild(self):
        """当索引中陈旧/删除条目占比超过 30% 时自动重建"""
        if self._faiss_index is None or self._faiss_index.ntotal == 0:
            return
        active_count = len(self._id_to_index)
        invalid_count = self._faiss_index.ntotal - active_count
        if invalid_count <= 0:
            return
        ratio = invalid_count / self._faiss_index.ntotal
        if ratio > 0.3:
            print(
                f"[VectorStore] 陈旧条目占比 {ratio:.0%} 超过阈值(30%)，"
                f"正在重建索引（{self._faiss_index.ntotal} -> {active_count}）..."
            )
            # 将 _vectors / _metadata 与 _id_to_index 对齐（丢弃已删除条目）
            active_set = set(self._id_to_index.keys())
            for vid in list(self._vectors.keys()):
                if vid not in active_set:
                    del self._vectors[vid]
            for vid in list(self._metadata.keys()):
                if vid not in active_set:
                    del self._metadata[vid]
            self._rebuild_index()
            self._save()

    # ==================================================================
    # 公开 API —— 方法签名与旧版完全一致
    # ==================================================================

    def add(self, vector_id: str, embedding: List[float], metadata: Dict[str, Any]):
        """添加单条向量（若 ID 已存在则替换，旧索引位置标记为陈旧）"""
        if not FAISS_AVAILABLE:
            self._vectors[vector_id] = embedding
            self._metadata[vector_id] = metadata
            self._save()
            return

        # 惰性初始化索引
        if self._faiss_index is None:
            self._dim = len(embedding)
            self._faiss_index = faiss.IndexFlatIP(self._dim)

        # 若 ID 已存在：旧索引位置会通过 stale 检测在 search 时被过滤
        vec = np.array(embedding, dtype=np.float32)
        vec = _l2_normalize(vec)

        new_idx = self._faiss_index.ntotal
        self._faiss_index.add(vec.reshape(1, -1))

        self._id_to_index[vector_id] = new_idx
        self._index_to_id[new_idx] = vector_id

        self._vectors[vector_id] = embedding
        self._metadata[vector_id] = metadata

        self._save_faiss()
        self._save()
        self._maybe_rebuild()

    def add_batch(self, items: List[Dict[str, Any]]):
        """批量添加向量
        items: [{"id": str, "embedding": List[float], "metadata": Dict}]
        """
        if not FAISS_AVAILABLE:
            for item in items:
                self._vectors[item["id"]] = item["embedding"]
                self._metadata[item["id"]] = item.get("metadata", {})
            self._save()
            return

        if not items:
            return

        if self._faiss_index is None:
            self._dim = len(items[0]["embedding"])
            self._faiss_index = faiss.IndexFlatIP(self._dim)

        vec_list = []
        for item in items:
            vid = item["id"]
            emb = item["embedding"]

            v = np.array(emb, dtype=np.float32)
            v = _l2_normalize(v)
            vec_list.append(v)

            self._vectors[vid] = emb
            self._metadata[vid] = item.get("metadata", {})

        matrix = np.array(vec_list, dtype=np.float32)
        start_idx = self._faiss_index.ntotal
        self._faiss_index.add(matrix)

        for i, item in enumerate(items):
            vid = item["id"]
            idx = start_idx + i
            self._id_to_index[vid] = idx
            self._index_to_id[idx] = vid

        self._save_faiss()
        self._save()
        self._maybe_rebuild()

    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """相似度检索（IndexFlatIP + L2 归一化 = 余弦相似度）"""
        if not FAISS_AVAILABLE:
            return self._search_numpy(query_embedding, top_k, filters)

        if self._faiss_index is None or self._faiss_index.ntotal == 0:
            return []

        # 归一化查询向量
        q = np.array(query_embedding, dtype=np.float32)
        q = _l2_normalize(q).reshape(1, -1)

        # 过度检索：为后续过滤（stale / deleted / filters）预留余量
        active_count = len(self._id_to_index)
        if active_count <= 0:
            return []
        search_k = min(
            self._faiss_index.ntotal,
            max(top_k * 10, top_k + (self._faiss_index.ntotal - active_count) * 2),
        )

        scores, indices = self._faiss_index.search(q, search_k)

        results: List[Dict[str, Any]] = []
        seen: set = set()
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:
                break
            idx = int(idx)
            vid = self._index_to_id.get(idx)
            if vid is None or vid in seen:
                continue

            # ---- stale 检测：如果该 id 当前指向的行号 != idx，说明该行是陈旧/已删除/已替换的 ----
            if self._id_to_index.get(vid) != idx:
                continue
            if vid not in self._metadata:
                continue

            # 元数据过滤
            meta = self._metadata[vid]
            if filters:
                matched = True
                for key, value in filters.items():
                    if meta.get(key) != value:
                        matched = False
                        break
                if not matched:
                    continue

            seen.add(vid)
            results.append(
                {
                    "id": vid,
                    "score": float(score),
                    "metadata": meta,
                }
            )
            if len(results) >= top_k:
                break

        return results[:top_k]

    def _search_numpy(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """numpy 降级实现（与旧版完全等价）"""
        if not self._vectors:
            return []

        q = np.array(query_embedding, dtype=np.float32)
        q = _l2_normalize(q)

        results = []
        for vid, embedding in self._vectors.items():
            v = np.array(embedding, dtype=np.float32)
            v = _l2_normalize(v)
            if np.linalg.norm(v) == 0:
                continue
            similarity = float(np.dot(q, v))

            meta = self._metadata.get(vid, {})
            if filters:
                skip = False
                for key, value in filters.items():
                    if meta.get(key) != value:
                        skip = True
                        break
                if skip:
                    continue

            results.append({"id": vid, "score": similarity, "metadata": meta})

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

    def delete(self, vector_id: str):
        """删除向量（从活跃映射中移除，陈旧条目在 search 中被过滤；达到阈值自动 rebuild）"""
        if not FAISS_AVAILABLE:
            self._vectors.pop(vector_id, None)
            self._metadata.pop(vector_id, None)
            self._save()
            return

        if vector_id in self._id_to_index:
            # 从活跃映射中移除 → search 时 stale 检测会过滤掉对应 FAISS 行
            del self._id_to_index[vector_id]
            # 立即从 JSON 源数据中移除，确保持久化一致
            self._vectors.pop(vector_id, None)
            self._metadata.pop(vector_id, None)
            self._save_faiss()
            self._save()
            self._maybe_rebuild()

    def delete_by_document(self, document_id: int) -> int:
        """按文档 ID 删除所有相关向量，返回删除数量"""
        if not FAISS_AVAILABLE:
            to_delete = [
                vid
                for vid, meta in self._metadata.items()
                if meta.get("document_id") == document_id
            ]
            for vid in to_delete:
                self._vectors.pop(vid, None)
                self._metadata.pop(vid, None)
            if to_delete:
                self._save()
            return len(to_delete)

        to_delete = [
            vid
            for vid, meta in self._metadata.items()
            if meta.get("document_id") == document_id and vid in self._id_to_index
        ]
        for vid in to_delete:
            del self._id_to_index[vid]
            self._vectors.pop(vid, None)
            self._metadata.pop(vid, None)

        if to_delete:
            self._save_faiss()
            self._save()
            self._maybe_rebuild()
        return len(to_delete)

    def clear(self):
        """清空所有向量"""
        self._vectors = {}
        self._metadata = {}

        if FAISS_AVAILABLE:
            self._id_to_index = {}
            self._index_to_id = {}
            if self._dim is not None:
                self._faiss_index = faiss.IndexFlatIP(self._dim)
            else:
                self._faiss_index = None
            self._save_faiss()

        self._save()

    def count(self) -> int:
        """返回当前有效向量数量"""
        if not FAISS_AVAILABLE:
            return len(self._vectors)
        return len(self._id_to_index)


# ========================================================================
# 全局单例
# ========================================================================
vector_store = VectorStore()
