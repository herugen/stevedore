# Prefect 本地环境部署指南

本文档记录了如何在一台全新的机器上，从零搭建并运行本项目的 Prefect 3.0 环境，包括依赖安装、Block 注册、Deployment 部署以及 Docker Worker 的启动。

## 1. 环境准备

1. 安装 Docker（包含 Docker Compose v2）。
2. 确保以下服务可用：
   - **Prefect Orion Server**：默认运行在宿主机 `http://127.0.0.1:4200`。
   - **Cobalt 服务**：默认 `http://localhost:9100`，用于获取下载链接。
   - **MinIO**：默认访问 `http://127.0.0.1:9100`，需要存在 bucket `stevedore`，访问凭据 `admin/admin123`。
3. 克隆仓库到本地：
   ```bash
   git clone https://github.com/herugen/stevedore.git
   cd stevedore
   ```
4. 复制本地环境变量模板（Compose 依赖该文件）：
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

本仓库提供了 Docker Compose 文件，可以依次执行 Block 注册、Deployment 应用以及启动 Worker：

```bash
docker compose -f docker/docker-compose.yml up
```

- `register-blocks` 服务会运行 `scripts/register_local_blocks.py`，在 Prefect 中创建：
  - `CobaltSettings` Block：保存 Cobalt API 配置。
  - `AwsCredentials`、`S3Bucket` 和 `MinIOBucket` Block：用于访问 MinIO。
- `apply-deployment` 服务会运行 `deployments/local_download_worker.py`，创建 `cobalt-video-download/cobalt-download-worker` 部署，指定工作池 `cobalt-downloads`。
- `downloader` 服务启动 Prefect Worker，监听 `cobalt-downloads` 工作池。

> Compose 默认会从 GitHub Container Registry 拉取镜像 `ghcr.io/herugen/stevedore-downloader:latest`；如需使用本地镜像，可修改 `docker/docker-compose.yml` 中的 `image` 与 `build` 配置。

> 如果你选择手动执行脚本，也可以在宿主机运行：
> ```bash
> export $(grep -v '^#' profiles/local.env | xargs)
> uv run python scripts/register_local_blocks.py
> uv run python deployments/local_download_worker.py
> ```
> 然后再启动 Worker。

> 若希望在 Prefect CLI 中使用相同配置，可执行：
> ```bash
> prefect profile create local --from-file profiles/local.toml
> prefect profile use local
> ```


## 4. 启动 Worker（可选手动方式）

若希望在 Compose 之外单独启动 Worker，可以运行：

```bash
docker run --rm \
  -e PREFECT_API_URL=http://host.docker.internal:4200/api \
  -e PREFECT_LOGGING_LEVEL=INFO \
  -v /var/run/docker.sock:/var/run/docker.sock \
  ghcr.io/herugen/stevedore-downloader:latest
```

> Linux 环境请将 `host.docker.internal` 替换为宿主机 IP。

## 5. 验证部署

1. 打开 Prefect UI（默认 `http://127.0.0.1:4200`），在 `Work Pools` 中确认 `cobalt-downloads` 存在。
2. 在 `Deployments` 页面确认 `cobalt-video-download/cobalt-download-worker` 已注册。
3. 触发一次部署运行：
   ```bash
   prefect deployment run cobalt-video-download/cobalt-download-worker \
     --param source_url="https://example.com/video.mp4" \
     --param task_id="demo-run"
   ```
4. 在 Worker 日志中确认任务执行成功，视频文件应已上传到 MinIO（路径示例：`s3://stevedore/demo-run/download/...`）。

## 6. 常见问题

- **无法连接 Prefect API**：确认 `PREFECT_API_URL` 是否指向正确地址，容器内访问本地服务需使用 `host.docker.internal` 或宿主机 IP。
- **MinIO 上传失败**：确认 Block 已注册，Bucket 名称/凭据是否正确，MinIO 服务是否允许外部访问。
- **Cobalt 调用失败**：检查 Cobalt 服务是否运行，以及 `COBALT_BASE_URL` 是否设置正确。

## 7. 后续扩展

- 新增任务或 Worker 时，可以复制 `docker/downloader` 目录并调整 Dockerfile、EntryPoint；同时在 `docker/docker-compose.yml` 添加新的服务块。
- CI 已提供矩阵构建镜像示例，可将新的 Dockerfile 加入 `.github/workflows/build-and-push.yaml` 中的 matrix。
- 建议记录每个 Worker 的 Block 名称、Work Pool、Deployment 参数，保证团队协作时一致性。

> 如果在运行过程中遇到新的需求或问题，欢迎更新此文档，确保所有成员都能顺利复现环境。

