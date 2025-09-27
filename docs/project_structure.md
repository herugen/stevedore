# Prefect 3 项目结构约定

本文档描述了本仓库遵循的 Prefect 3.0 项目结构与代码组织约定，便于团队成员统一认知与协作。

## 顶层布局

- `flows/`：保存 Prefect Flow 定义；按业务域或产品线拆分子目录，Flow 只负责编排任务、控制依赖与调度配置。
- `tasks/`：存放可复用的任务函数或子流程；按功能模块拆分文件，如 `io.py`、`transforms.py` 等，Flow 通过导入这些任务组合业务逻辑。
- `blocks/`：封装 Prefect Block 定义与注册逻辑（如凭据、存储、通知）；推荐提供 `__init__.py` 与注册脚本（如 `register.py`）。
- `deployments/`：管理 Prefect 部署脚本或声明（Python/YAML），按环境或用途拆分文件，例如 `prod.py`、`dev.py`。部署脚本负责引用 Flow 并定义工作池、参数及调度。
- `profiles/`：集中存放 Prefect Profile 或环境配置模板（如 `.prefect/profiles.toml` 片段、`.env.example`），用于本地与服务器环境的配置对齐。
- `tests/`：使用 `pytest` 等框架对任务、辅助函数及 Flow 进行单元与集成测试，确保逻辑正确性与回归验证。
- `scripts/`：与项目相关的辅助脚本（如 Block 注册、调试、数据模拟、CI 命令），避免散落在根目录。
- `docs/`：文档类内容（本文档、使用指南、架构说明等），保持持续更新。
- `docker/`：容器化相关文件（`Dockerfile`、`docker-compose.yml`、镜像配置），满足部署或 CI 需求。
- 项目根目录：放置 `pyproject.toml`/`requirements.txt` 等依赖声明、`README.md`、`main.py` 或 `serve.py` 等运行入口文件。

## 编码与配置约定

1. **Flow 与 Task 分离**：Flow 不直接包含业务细节，所有可复用逻辑放入 `tasks/`，强化测试与复用性。
2. **Block 管理**：Block 定义集中在 `blocks/`，统一在 `scripts/` 或 `deployments/` 中注册，避免重复创建。
3. **配置优先使用 Prefect 设置**：敏感信息或环境变量通过 Prefect Blocks、Variables 或 `.env` 文件管理，不在代码里硬编码。
4. **测试覆盖**：新增 Flow 或关键 Task 时同步编写测试用例，`tests/` 中按模块命名文件，如 `test_tasks_io.py`、`test_flow_data_pipeline.py`。
5. **文档同步**：新增目录或重要模块时更新本文档或其他 `docs/` 文件，保持结构与约定的一致性。
6. **CI/CD 集成**：推荐在 `scripts/` 或 `.github/`（若使用 GitHub）中加入 Lint、Test、Deployment 等自动化流程脚本。

## 后续工作指引

- 新建 Flow 时：
  1. 在 `tasks/` 中实现必要任务并编写测试；
  2. 在 `flows/` 中编排 Flow，确保类型注解与文档齐备；
  3. 在 `deployments/` 中定义部署脚本并验证本地运行；
  4. 更新 `docs/`（运行说明或架构图）。
- 新增 Block 时：
  1. 在 `blocks/` 中定义 Block 类；
  2. 在 `scripts/` 中提供注册脚本；
  3. 更新 `profiles/` 或 `.env.example` 说明必需的配置。

遵循上述约定可以确保 Prefect 3.0 项目的高可维护性与一致性，便于后续扩展与团队协作。

