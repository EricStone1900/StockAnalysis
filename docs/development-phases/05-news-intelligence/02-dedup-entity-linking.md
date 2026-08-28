# 05-02 去重、聚类和实体关联

## 目标

将转载新闻合并为事件候选，并通过Security Master关联股票代码。

## 实施步骤

### 1. 去重顺序

```text
canonical URL
  -> exact content hash
  -> normalized title hash
  -> SimHash/MinHash near duplicate
  -> vector similarity within time window
```

先运行低成本确定性方法，再运行向量检索。

### 2. 聚类键

候选聚类综合实体、时间窗口、标题相似度和事件词。不要仅因两条新闻提到同一公司就合并。

```python
class NewsEventCandidate(BaseModel):
    candidate_id: str
    news_ids: list[str]
    representative_title: str
    candidate_symbols: list[SymbolCandidate]
    published_at_range: TimeRange
    freshness: DataFreshness
```

### 3. Entity Linker

读取Security Master的代码、全称、简称、曾用名、品牌和子公司映射。

```python
if match.confidence < settings.minimum_entity_confidence:
    candidate.requires_manual_mapping = True
```

低置信度不能直接进入重要股票事件。

### 4. pgvector

向量用于候选召回，不作为唯一去重结论。保存embeddingModelVersion和输入contentHash。

## 测试案例

1. 三家媒体转载同一公告只生成一个候选。
2. 同一公司两件不同事件不被错误合并。
3. 公司曾用名能关联历史证券。
4. 常见歧义简称进入人工映射。
5. embedding模型升级不会覆盖旧聚类版本。

## 完成条件

- 去重和聚类有版本化指标。
- 候选事件保留全部newsIds。
- 实体关联可解释匹配来源和置信度。

