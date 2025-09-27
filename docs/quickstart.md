# Prefect 本地环境部署指南

本文档记录了如何在一台全新的机器上，从零搭建并运行本项目的 Prefect 3.0 环境，包括依赖安装、Block 注册、Deployment 部署以及 Docker Worker 的启动。

## 1. 环境准备

1. 安装 Docker。
2. 确保以下服务可用：
   - **Prefect Orion Server**：默认运行在宿主机 `http://127.0.0.1:4200`。
   - **Cobalt 服务**：默认 `http://localhost:9100`，用于获取下载链接。
   - **MinIO**：默认访问 `http://127.0.0.1:9100`，需要存在 bucket `stevedore`，访问凭据 `admin/admin123`。
3. 克隆仓库到本地：
   ```bash
   git clone https://github.com/herugen/stevedore.git
   cd stevedore
   ```
4. 复制本地环境变量模板：
   - macOS / Windows：
     ```bash
     cp profiles/local.env.example profiles/local.env
     ```
   - Linux：
     ```bash
     cp profiles/linux.env.example profiles/local.env
     # 如有需要，将 172.17.0.1 替换为宿主机实际 IP
     ```

## 2. Prefect Server 与外部服务

- Prefect Server 建议通过官方 Docker 镜像或已有部署启动，目标地址保持 `http://127.0.0.1:4200`。
- 若 Cobalt 或 MinIO 运行在容器中，请确保可以从 Prefect Worker 容器访问宿主机，可使用 `host.docker.internal`（macOS/Windows）或宿主机局域网 IP（Linux）。

## 3. Block 注册与 Deployment 应用

本仓库提供了容器化脚本，帮助自动化完成 Block、工作池与 Deployment 注册；Worker 则根据机器能力单独启动。

### 3.1 初始化 Prefect 资源

1. **创建 Work Pool**（若尚未存在）：

   ```bash
   scripts/create_work_pool.sh
   # 或指定名称/类型
   WORK_POOL_NAME=cobalt-downloads WORK_POOL_TYPE=docker scripts/create_work_pool.sh
   ```
2. **注册 Blocks**：

   ```bash
   scripts/register_local_blocks.sh
   # 支持覆盖环境文件路径
   STEVEDORE_ENV_FILE=my.env scripts/register_local_blocks.sh
   ```

- `register_local_blocks.sh` 会加载 `profiles/local.env`（可通过 `STEVEDORE_ENV_FILE` 覆盖），保存 Cobalt、MinIO 相关 Block。

### 3.2 注册本地 Deployment

```bash
scripts/apply_local_deployments.sh
```

将注册 `cobalt-video-download/cobalt-download-worker` 部署，并指向 `cobalt-downloads` 工作池。

### 3.3 按需启动 Worker

在具备下载能力的机器上执行：

```bash
scripts/start_downloader_worker.sh --name my-cobalt-worker
```

可用环境变量：`STEVEDORE_ENV_FILE` 指定配置文件，`STEVEDORE_IMAGE` 指定镜像，`WORK_POOL_NAME` 覆盖工作池名称。

### 3.4 触发单次部署运行

```bash
scripts/run_deployment_once.sh --param source_url="https://x.com/elonmusk/status/1971866050632602048" --param task_id="demo-01"
```

默认从 `profiles/local.env` 读取 Prefect 连接信息，可通过 `STEVEDORE_ENV_FILE` 指定其他文件。

> 默认使用镜像 `ghcr.io/herugen/stevedore-downloader:latest`；如需使用本地镜像，可通过环境变量 `STEVEDORE_IMAGE` 覆盖。

- 如果你选择手动执行脚本，也可以在宿主机运行（确保已安装 `uv` 或适当的 Python 环境）：
  ```bash
  export $(grep -v '^#' profiles/local.env | xargs)
  uv run stevedore register-blocks --env-file profiles/local.env
  uv run stevedore apply-deployments --env-file profiles/local.env
  ```

  然后再启动 Worker。

> 若希望在 Prefect CLI 中使用相同配置，可执行：
>
> ```bash
> prefect profile create local --from-file profiles/local.toml
> prefect profile use local
> ```

## 4. 验证部署

1. 打开 Prefect UI（默认 `http://127.0.0.1:4200`），在 `Work Pools` 中确认 `cobalt-downloads` 存在。
2. 在 `Deployments` 页面确认 `cobalt-video-download/cobalt-download-worker` 已注册。
3. 在 Worker 日志中确认任务成功、文件已写入 MinIO（示例路径：`s3://stevedore/demo-run/download/...`）。

## 5. 常见问题

- **无法连接 Prefect API**：确认 `PREFECT_API_URL` 是否指向正确地址，容器内访问本地服务需使用 `host.docker.internal` 或宿主机 IP。
- **MinIO 上传失败**：确认 Block 已注册，Bucket 名称/凭据是否正确，MinIO 服务是否允许外部访问。
- **Cobalt 调用失败**：检查 Cobalt 服务是否运行，以及 `COBALT_BASE_URL` 是否设置正确。

## 6. 后续扩展

- 新增任务或 Worker 时，可以复制 `docker/downloader` 目录并调整 Dockerfile、EntryPoint；必要时在 `.github/workflows/build-and-push.yaml` 中新增构建配置。
- CI 已提供矩阵构建镜像示例，可将新的 Dockerfile 加入 `.github/workflows/build-and-push.yaml` 中的 matrix。
- 建议记录每个 Worker 的 Block 名称、Work Pool、Deployment 参数，保证团队协作时一致性。

> 如果在运行过程中遇到新的需求或问题，欢迎更新此文档，确保所有成员都能顺利复现环境。
