# 新增 Prefect Task 与独立 Worker 指南

本文档记录在本仓库内扩展新的 Prefect Task、Flow 编排逻辑以及配套 Worker 的推荐流程，特别适用于为现有 Flow 增加额外任务（如音频抽取）并希望由专门 Worker 承载的场景。

## 适用范围

- 在既有 Flow 中串联新的 Prefect `@task`，强化编排逻辑。
- 为任务提供独立的运行环境/Worker（如 FFmpeg 音频处理）。
- 同步更新部署、脚本、配置与文档，保持团队协作一致性。

## 前置准备

1. 明确业务需求及输入/输出：例如「下载→音频提取」的对象路径传递、失败重试策略等。
2. 校验依赖 Block：确认是否复用 `MinIOBucket`、`CobaltSettings` 或需要新增 Block。
3. 统一命名约定：Task 名称、Flow 参数、工作池（Work Pool）、Worker 镜像/脚本命名保持一致。
4. 规划 Worker 运行环境：确定镜像需要安装的工具（如 FFmpeg）以及要注入的环境变量。

## 标准步骤

1. **实现 Task**
   - 在 `stevedore/tasks/` 中新增或扩展模块，遵循已有类型注解、日志、异常封装风格（参考 `downloads.py`、`audio.py`）。
   - 如果多个任务共享逻辑，可提取辅助函数或工具模块。
   - 添加/更新 `tests/` 下的 pytest 用例；通过 `AsyncMock` 等手段隔离外部服务依赖。

2. **更新 Flow 编排**
   - 评估是否拆分为多个 Flow（例如 `cobalt_video_download_flow` 与 `audio_extraction_flow`），由父 Flow 统一调度。
   - 父 Flow 可通过 `prefect.deployments.run_deployment` 触发各子 Flow，使不同阶段运行在各自的 Work Pool。
   - 注意参数传递与结果消费方式（例如从下载 Flow 的状态中获取视频路径再传给音频 Flow）。

3. **部署与 Worker**
   - 在 `stevedore/deployments/` 为每个子 Flow 创建部署文件，指定其 Work Pool（如下载用 `cobalt-downloads`，音频用 `audio-processing`）。
   - 为专用 Worker 准备 Dockerfile（如 `docker/audio-worker/`）与启动脚本（如 `scripts/start_audio_worker.sh`），确保镜像包含所需工具（FFmpeg 等）。
   - 使用 `scripts/create_work_pool.sh` 或 Prefect CLI 创建对应 Work Pool，并在文档中记录默认名称/类型。

4. **配置与环境**
   - 在 `profiles/` 目录下的模板文件中补充新 Worker 的环境变量（工作池名称、镜像标签等）。
   - 更新 `.env.example`/`local.toml` 说明新任务所需的配置项。

5. **文档与脚本同步**
   - 更新 `docs/project_structure.md`、`docs/quickstart.md` 等文档，说明新增任务、Worker 的职责与启动方式。
   - 如需一键化脚本（部署、Block 注册等），同步改动 `scripts/` 目录中的相关脚本。

6. **验证流程**
   - 运行 `pytest` 覆盖新增任务/Flow 的单元测试。
   - 执行 `scripts/register_local_blocks.sh` 与 `scripts/apply_local_deployments.sh`，确认部署在 Prefect 中注册成功。
   - 分别启动下载 Worker 与音频 Worker，触发 Flow，验证整个链路是否按预期产出视频与音频对象。

## 检查清单

- [ ] 新任务代码、日志、异常处理到位。
- [ ] Flow 参数与返回值与调用方同步。
- [ ] 部署文件/脚本更新，包含新任务所需配置。
- [ ] Worker 镜像、启动脚本、Work Pool 已准备。
- [ ] Profiles 与 `.env.example` 更新说明。
- [ ] 文档同步，包含运行步骤与注意事项。
- [ ] 本地或测试环境验证通过，记录测试结果。

## 经验分享

- 复用现有脚本/镜像时，避免复制粘贴引起的配置漂移，可通过 `docker build --build-arg` 或公共基础镜像复用。
- 多个 Worker 协同时，推荐在部署 YAML 中使用显式标签、队列名称，便于运维排查。
- 若某些任务只适合异步/专用 Worker，可考虑改为子 Flow 并通过 `prefect.deployments.run_deployment` 调度，进一步隔离资源。


