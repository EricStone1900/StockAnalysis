# News 06-01 骨架、采集和证据切片

## 实施步骤

1. 建立Source、LicensePolicy、NewsItem、EvidenceArtifact和IngestionRun。
2. 最小Use Case为“从固定RSS/JSON Fixture采集一条新闻并保存原文Artifact引用”。
3. 标准化标题、正文Hash、URL、作者、publishedAt、collectedAt、availableAt、语言和来源可靠性。
4. 原文进入MinIO，数据库只保存URI、Hash、许可和摘要字段。
5. 外部正文标记UNTRUSTED，不允许其中内容改变工具权限或系统配置。

```ts
interface NewsProvenance {
  sourceId: string;
  sourceUrl: string;
  publishedAt: string;
  collectedAt: string;
  availableAt: string;
  licensePolicyId: string;
  contentHash: string;
}
```

## 测试

- URL/Hash重复采集幂等。
- 缺发布时间、时区错误、正文损坏和许可禁止存档。
- 原文Hash不匹配时证据不可用。

