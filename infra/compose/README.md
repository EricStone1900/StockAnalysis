# 本地基础设施

推荐入口（Mac/Linux一致）：

```sh
bash scripts/local-stack.sh config research
bash scripts/local-stack.sh up infra
bash scripts/local-stack.sh up research
bash scripts/local-stack.sh status research
```

以上命令在仓库根执行。`infra`只启动存储、消息及观测基础设施；`research`增加市场数据、量化、BFF和Web；`manual-services`再增加组合、治理、执行服务；`full-demo`包含当前Compose列出的服务和Fake Agent，不包含尚未接入的真实Workflow/自动研究闭环。

Web地址为`http://127.0.0.1:5173`，BFF为3008端口。Vite代理`/api`到BFF；容器使用服务名，本机Vite默认使用127.0.0.1。当前BFF身份头仍是开发契约，只允许本地使用。端口默认绑定loopback。

`config`仅校验配置，不启动服务、不显示凭据。首次`up`生成缺失Secret；不覆盖已有Secret或数据卷。数据库已存在时沿用现有凭据，禁止通过删除数据卷修复密码不匹配。

执行创建入口尚未接入权威授权，默认返回不可用；所有执行写入口还要求服务身份认证。不要把测试allow stub接入运行配置。容器健康不代表业务闭环验收完成。

资源预算尚未实测；不要把`full-demo`作为Mac最低配置承诺。启动后用`docker stats --no-stream`记录机器架构、内存及各容器占用；真实数据任务须另外记录峰值内存与耗时。

运行 `../../scripts/infra-up.sh` 启动最小infra组合；Temporal在full-demo组合中显式启用。脚本只创建被 `.gitignore` 忽略的本地开发 Secret 文件；不得将其提交。

PostgreSQL 为每个服务创建独立 Database/User。服务凭证在阶段 01-03 通过 Secret 文件引用；禁止跨库连接或共享表。Redis 仅用于可丢失缓存、限流和短期锁，不能保存领域事实。MinIO Artifact 必须保存内容 Hash 与版本元数据。
