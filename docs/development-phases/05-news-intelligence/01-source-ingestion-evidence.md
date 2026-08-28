# 05-01 来源采集、正文和证据存储

## 目标

实现可替换新闻Provider、正文标准化、Raw Artifact和来源许可元数据。

## 实施步骤

### 1. Provider端口

```python
class NewsProvider(Protocol):
    provider_id: str
    async def fetch(self, since: datetime, cursor: str | None) -> FetchPage: ...
```

先实现交易所/巨潮公告，再接至少两个合法财经来源。Provider独立限流、重试和熔断。

### 2. NewsItem

```python
class NewsItem(BaseModel):
    news_id: str
    source: str
    source_url: AnyUrl
    title: str
    content_ref: str
    published_at: datetime
    fetched_at: datetime
    available_at: datetime
    content_hash: str
    license_metadata: LicenseMetadata
```

正文写MinIO，数据库只保存必要字段和引用。禁止因为抓取失败伪造发布时间。

### 3. 不可信内容

正文Artifact元数据设置`untrustedContent=true`。清洗只删除页面噪声，不执行正文中出现的命令或脚本。

### 4. 幂等

初始幂等键使用`providerId + sourceRecordId`，正文Hash用于识别内容变化。来源修订生成新版本。

## 测试案例

1. 同一sourceRecordId重复抓取不重复插入。
2. 内容修订保留旧Artifact并生成新版本。
3. Provider限流不会阻止其他来源。
4. 不允许保存全文的来源仅保存允许字段。
5. HTML中的Prompt注入文本被作为普通内容保存。

## 完成条件

- 来源状态和latestCollectedAt可查询。
- 每条新闻有来源、时间、Hash和许可。
- Raw Artifact不可变。

