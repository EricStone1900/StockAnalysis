# quant-research-service人工验收

本文命令在阶段03代码、脚本和Ubuntu Compose覆盖文件全部实现后执行。验收人自行操作；任何关键步骤失败立即停止并记录，不得跳过。

## 一、准备验收信息

在Mac终端设置连接信息，值由验收人替换：

```bash
export STAGE03_BRANCH='stage/03-quant-research'
export UBUNTU_USER='替换为SSH用户名'
export UBUNTU_HOST='替换为服务器IP或域名'
export STAGE03_DIR='/opt/stock-analysis'
export STAGE03_DATA_VERSION='替换为阶段02发布的真实DataVersion'
export STAGE03_SOURCE_RELEASE='替换为固定investment_data Release Tag'
```

确认SSH和服务器架构：

```bash
ssh "$UBUNTU_USER@$UBUNTU_HOST" 'uname -a; uname -m; docker --version; docker compose version; git --version'
```

预期SSH成功，Docker、Compose和Git均可用。若Git缺失，执行`sudo apt update && sudo apt install -y git`；若Docker或Compose缺失，先按[Docker官方Ubuntu安装说明](https://docs.docker.com/engine/install/ubuntu/)安装Docker Engine、Buildx和Compose Plugin，然后重新运行检查命令。

继续记录服务器资源：

```bash
ssh "$UBUNTU_USER@$UBUNTU_HOST" 'nproc; free -h; df -h /; timedatectl status'
```

记录Ubuntu是`x86_64`还是`aarch64`、CPU、内存、磁盘和时区。服务器防火墙或云安全组只允许可信来源访问SSH，不开放3001、5433、4222、9000、9001和8222。Docker发布端口可能绕过UFW，因此仍必须使用后文的`127.0.0.1`端口绑定检查。

## 二、在Mac完成候选验证

```bash
cd /Users/huangbosong/Documents/ChatGPT/StockAnalysis
git status --short
./scripts/stage03-verify-mac.sh
./scripts/stage03-record-evidence.sh artifacts/stage03/mac
git diff --check
```

预期所有检查通过。人工查看`git status --short`，不得提交`.env`、Secret、`.venv`、缓存、模型大文件或数据卷。

## 三、提交并推送到GitHub

首次创建阶段分支时执行：

```bash
git switch -c "$STAGE03_BRANCH"
git add -- services/quant-research-service packages/contracts \
  infra/compose/docker-compose.stage03-ubuntu.yml scripts/stage03-*.sh \
  docs/development-roadmap-v2/03-quant-research-service
git diff --cached --check
git diff --cached
git commit -m 'feat(quant): 完成阶段03验收候选'
git push -u origin "$STAGE03_BRANCH"
git rev-parse HEAD
```

如果分支已经存在，跳过`git switch -c`。复制最后输出的完整Commit SHA，以下记为`STAGE03_COMMIT`。确认GitHub上的分支和该SHA可见后再继续。

## 四、Ubuntu首次拉取代码

服务器首次部署执行：

```bash
ssh "$UBUNTU_USER@$UBUNTU_HOST"
export STAGE03_BRANCH='stage/03-quant-research'
export STAGE03_DIR='/opt/stock-analysis'
sudo install -d -o "$(id -un)" -g "$(id -gn)" "$STAGE03_DIR"
git clone --branch "$STAGE03_BRANCH" https://github.com/EricStone1900/StockAnalysis.git "$STAGE03_DIR"
cd "$STAGE03_DIR"
git fetch origin "$STAGE03_BRANCH"
git switch --detach STAGE03_COMMIT
git rev-parse HEAD
git status --porcelain
```

把命令中的`STAGE03_COMMIT`替换成第三步复制的真实SHA。若仓库私有，先在GitHub配置只读Deploy Key，再使用`git@github.com:EricStone1900/StockAnalysis.git`克隆。预期SHA完全一致，`git status --porcelain`无输出。

从本节到第十节均在同一个Ubuntu SSH会话中执行；命令提示符应位于服务器，而不是Mac。

后续更新服务器时不重新克隆：

```bash
cd "$STAGE03_DIR"
git fetch origin "$STAGE03_BRANCH"
git switch --detach STAGE03_COMMIT
```

## 五、生成服务器专用配置

不得运行会写入固定本地密码的开发脚本。执行阶段03提供的初始化脚本：

```bash
cd "$STAGE03_DIR"
umask 077
./scripts/stage03-server-init.sh
find infra/compose/secrets -type f -exec stat -c '%a %n' {} \;
```

预期Secret权限为`600`，目录权限为`700`，所有Secret均被Git忽略。人工检查`infra/compose/docker-compose.stage03-ubuntu.yml`：端口列表必须使用`!override`替换基础配置，并全部绑定`127.0.0.1`；Strategy Runner必须为只读文件系统、无外网、无生产Secret和受限CPU/内存。再检查最终合并配置：

```bash
docker compose -f infra/compose/docker-compose.yml \
  -f infra/compose/docker-compose.stage03-ubuntu.yml config > /tmp/stage03-compose.yml
grep -n '0.0.0.0' /tmp/stage03-compose.yml
```

预期`grep`无输出；如有任何`0.0.0.0`端口映射，立即停止验收。

## 六、原生构建并启动

```bash
cd "$STAGE03_DIR"
docker compose -f infra/compose/docker-compose.yml \
  -f infra/compose/docker-compose.stage03-ubuntu.yml build --pull quant-research-service
docker compose -f infra/compose/docker-compose.yml \
  -f infra/compose/docker-compose.stage03-ubuntu.yml up -d
docker compose -f infra/compose/docker-compose.yml \
  -f infra/compose/docker-compose.stage03-ubuntu.yml ps
docker image inspect stock-analysis-infra-quant-research-service \
  --format '{{.Id}} {{.Architecture}} {{.Os}}'
```

预期全部必需容器为`running`或`healthy`，镜像架构与`uname -m`对应。不得依赖Mac构建的镜像。

## 七、迁移、健康与契约检查

```bash
./scripts/stage03-migrate.sh
./scripts/stage03-migrate.sh
curl --fail http://127.0.0.1:3001/live
curl --fail http://127.0.0.1:3001/ready
curl --fail http://127.0.0.1:3001/openapi.json -o /tmp/stage03-openapi.json
```

迁移连续执行两次都应成功。`/live`返回`UP`；`/ready`返回`UP`且PostgreSQL、MinIO、NATS、market-data均可用。检查OpenAPI存在Snapshot、Factor、Model、Backtest和Strategy接口，且不存在创建TradeProposal、Approval或Order的接口。

## 八、执行服务器自动化测试

```bash
./scripts/stage03-verify-ubuntu.sh
./scripts/stage03-record-evidence.sh artifacts/stage03/ubuntu
```

预期Ruff、Mypy、单元、集成、契约、E2E、安全与恢复测试全部通过，无跳过的强制用例。保存完整日志和退出码。

## 九、固定DataVersion端到端验收

先记录并核对真实数据输入：`investment_data`固定Release Tag、归档和Manifest SHA-256、来源策略版本、DataVersion、日期范围、证券数、总行数、缺失率、补充率、冲突率、质量报告与许可引用。不得使用浮动`latest`，也不得由量化服务直接访问第三方数据源。Fixture可验证功能，但不能替代本节真实日频数据验收。

若使用`assume_suspension_on_read`，还必须记录CloseGapHandlingPolicy Artifact、父`close-gap-index` URI/Hash、适用范围、审批引用、操作者和`WARN`质量结论。人工抽样空洞股票日，确认原始价格仍为空、当日不可交易且未产生价格类因子或收益率；该策略只允许阶段03开发、研究和`CANDIDATE`验证，不得签署为`PASS`或正式READY快照。

```bash
export STAGE03_DATA_VERSION='替换为阶段02发布的真实DataVersion'
export STAGE03_SOURCE_RELEASE='替换为固定investment_data Release Tag'
./scripts/stage03-e2e.sh \
  --data-version "$STAGE03_DATA_VERSION" \
  --source-release "$STAGE03_SOURCE_RELEASE" \
  --repeat 2
```

人工确认两次运行的DataVersion、UniverseVersion、FactorSetVersion、ModelVersion和随机种子相同；股票池不包含未来成分；停牌、退市和持仓股处理符合规则；只有ACTIVE因子、模型和策略进入READY快照；CANDIDATE被拒绝；`NO_REBALANCE`不创建组合调仓批次，quant服务没有DecisionBudgetReservation或RebalanceBatch写接口。

两次运行的`canonicalContentHash`、快照行数和排序必须一致。输出必须包含DailyAnalysisSnapshot、DailyStrategySnapshot、回测明细、质量摘要和Artifact引用，不得包含最终BUY/SELL指令、订单、审批或Secret。

先只启用价格动量、波动率和流动性因子完成真实数据闭环。随后分别检查价值和质量因子：若历史估值、公告时间或修订链尚未满足阶段02门禁，确认它们保持`DRAFT`且快照明确记录降级原因；只有补充数据验证通过后才允许进入`CANDIDATE`，仍需正常准入流程才能成为`ACTIVE`。

## 十、PIT、失败与恢复验收

依次执行：

```bash
./scripts/stage03-failure-test.sh future-data
./scripts/stage03-failure-test.sh bad-artifact-hash
./scripts/stage03-failure-test.sh duplicate-event
./scripts/stage03-failure-test.sh partial-calculation
./scripts/stage03-failure-test.sh nats-outage
./scripts/stage03-failure-test.sh runner-isolation
```

预期未来数据、错误Hash和部分结果均不能发布READY；重复事件只产生一个Run；NATS恢复后Outbox只补发一次；失败期间上一READY快照仍可查询并明确标记`isStale=true`与`validUntil`；第三方Runner无法访问外网、数据库、宿主写目录或Secret，超时/OOM只影响自身任务并留下审计记录。

## 十一、Mac与Ubuntu结果对比

先退出Ubuntu SSH会话并回到Mac终端，再把Mac证据目录复制到服务器的临时验收目录：

```bash
scp -r artifacts/stage03/mac "$UBUNTU_USER@$UBUNTU_HOST:/tmp/stage03-mac-evidence"
ssh "$UBUNTU_USER@$UBUNTU_HOST" \
  "cd '$STAGE03_DIR' && ./scripts/stage03-compare-evidence.sh /tmp/stage03-mac-evidence artifacts/stage03/ubuntu"
```

预期Commit SHA、输入Artifact SHA-256、契约版本和`canonicalContentHash`完全一致；模型与回测指标在冻结容差内。任何输入Hash、PIT结果或规范内容Hash差异均判定`FAIL`。

## 十二、回滚演练与签署

重新连接Ubuntu并执行文档化的上一READY快照恢复：

```bash
ssh "$UBUNTU_USER@$UBUNTU_HOST"
export STAGE03_DIR='/opt/stock-analysis'
cd "$STAGE03_DIR"
./scripts/stage03-rollback-test.sh
./scripts/stage03-record-evidence.sh artifacts/stage03/final
```

确认恢复后API返回上一READY快照，数据库迁移状态一致，Artifact Hash校验通过。验收记录必须填写：Commit SHA、Git Tag、镜像Digest、CPU架构、Python/Qlib版本、迁移版本、OpenAPI/AsyncAPI版本、DataVersion、各Registry版本、测试报告路径、风险、回滚目标、验收时间和签署人。

以下全部满足才可签署`PASS`：

- [ ] 固定DataVersion可重建因子、模型、回测和两类快照。
- [ ] PIT、未来泄漏、样本外、成本、停牌和生存偏差测试通过。
- [ ] 快照原子发布、失败保旧、重复幂等与Hash恢复通过。
- [ ] Plugin SDK、四个初始策略、NO_REBALANCE和Runner隔离通过。
- [ ] 只有ACTIVE版本进入生产式快照，服务不拥有交易、审批或订单。
- [ ] Mac与Ubuntu规范内容一致，Ubuntu完整测试无强制用例跳过。
- [ ] 固定真实数据Release、输入Hash、来源策略、质量/对账和许可证据齐全。
- [ ] 价值/质量因子缺少PIT数据时被正确阻止，未使用当前值回填历史。
- [ ] 证据、风险、回滚方案和验收人签名齐全。

验收人填写以下记录，不得只勾选而不附证据：

| 字段 | 验收记录 |
|---|---|
| Commit SHA / Git Tag |  |
| Ubuntu版本与CPU架构 |  |
| 镜像名称与Digest |  |
| Python / Qlib / 数值依赖版本 |  |
| 数据库迁移版本 |  |
| OpenAPI / AsyncAPI / Plugin契约版本 |  |
| DataVersion及输入Artifact SHA-256 |  |
| 主数据Release Tag及归档/Manifest SHA-256 |  |
| 来源策略版本、质量/对账报告及许可引用 |  |
| 日期范围、证券/行数、缺失/补充/冲突率 |  |
| 估值、财务公告与修订链门禁结论 |  |
| Universe / FactorSet / Model / Strategy版本 |  |
| Mac / Ubuntu `canonicalContentHash` |  |
| 自动化测试报告路径 |  |
| 故障、隔离与回滚证据路径 |  |
| 已知风险和剩余限制 |  |
| 回滚目标Tag / 镜像Digest / READY快照 |  |
| 验收结论（PASS/FAIL） |  |
| 验收人和时间 |  |

签署后冻结DailyAnalysisSnapshot和DailyStrategySnapshot v1；未通过时保留证据并回到对应实施步骤修复，不得进入阶段04。
