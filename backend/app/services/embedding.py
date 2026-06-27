import hashlib
import numpy as np
from typing import List, Optional
from app.core.config import settings


class EmbeddingService:
    """文本向量化服务"""
    
    def __init__(self):
        self.provider = settings.EMBEDDING_PROVIDER
        self.model_name = settings.EMBEDDING_MODEL
        self._model = None
        self._cache = {}
        self._dimension = 768  # text2vec-base-chinese 默认维度
    
    def _get_model(self):
        """懒加载本地模型"""
        if self._model is None and self.provider == "local":
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.model_name)
                self._dimension = self._model.get_sentence_embedding_dimension()
            except Exception as e:
                print(f"加载本地Embedding模型失败: {e}, 将使用随机向量")
                self._model = False  # 标记为不可用
        return self._model
    
    def _embed_local(self, texts: List[str]) -> List[List[float]]:
        """本地模型向量化"""
        model = self._get_model()
        if model is False or model is None:
            return self._embed_mock(texts)
        
        embeddings = model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()
    
    def _embed_mock(self, texts: List[str]) -> List[List[float]]:
        """Mock模式：基于文本哈希生成伪随机向量"""
        embeddings = []
        for text in texts:
            # 使用MD5哈希作为种子生成确定性向量
            hash_val = hashlib.md5(text.encode()).hexdigest()
            np.random.seed(int(hash_val[:8], 16))
            vec = np.random.randn(self._dimension)
            vec = vec / np.linalg.norm(vec)  # 归一化
            embeddings.append(vec.tolist())
        return embeddings
    
    def embed(self, texts: List[str]) -> List[List[float]]:
        """批量向量化文本"""
        if not texts:
            return []
        
        # 使用缓存避免重复计算
        results = []
        texts_to_embed = []
        cache_indices = []
        
        for i, text in enumerate(texts):
            text_hash = hashlib.md5(text.encode()).hexdigest()
            if text_hash in self._cache:
                results.append((i, self._cache[text_hash]))
            else:
                texts_to_embed.append((i, text, text_hash))
                cache_indices.append(text_hash)
        
        if texts_to_embed:
            uncached_texts = [t[1] for t in texts_to_embed]
            
            if settings.MOCK_MODE or self.provider == "mock":
                new_embeddings = self._embed_mock(uncached_texts)
            elif self.provider == "local":
                new_embeddings = self._embed_local(uncached_texts)
            else:
                new_embeddings = self._embed_mock(uncached_texts)
            
            for (orig_idx, text, text_hash), embedding in zip(texts_to_embed, new_embeddings):
                self._cache[text_hash] = embedding
                results.append((orig_idx, embedding))
        
        # 按原始顺序排序
        results.sort(key=lambda x: x[0])
        return [emb for _, emb in results]
    
    def embed_query(self, text: str) -> List[float]:
        """向量化单个查询文本"""
        embeddings = self.embed([text])
        return embeddings[0] if embeddings else []
    
    @property
    def dimension(self) -> int:
        return self._dimension


embedding_service = EmbeddingService()
