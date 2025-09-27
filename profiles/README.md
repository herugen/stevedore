# Profiles

本目录用于保存不同环境下复现 Prefect 配置所需的模板文件，方便团队成员在新环境中快速对齐变量与 Profile。

## 文件说明

- `local.env.example`：本地开发所需的环境变量模板。复制为 `.env` 或 `local.env` 后加载即可。
- `local.toml`：示例 Prefect Profile 配置文件，可通过 `prefect profile create` / `prefect profile inspect` 导入。
- 其他环境（如 `dev`, `prod`）可以按相同命名规则添加对应的 `*.env.example` 与 `*.toml`。

## 使用方式

1. **环境变量**
   ```bash
   cp profiles/local.env.example .env
   export $(grep -v '^#' .env | xargs)  # 或使用 direnv/dotenv 工具
   ```

2. **Prefect Profile**
   ```bash
   prefect profile create local --from-file profiles/local.toml
   prefect profile use local
   ```

3. **切换环境**：当新增 `dev`、`prod` 等 Profile 时，重复上述步骤即可实现配置切换。

> 注意：实际凭据（如 MinIO 密钥）不应直接提交到仓库，可在 `.env` 中覆盖或通过 Prefect Blocks、Cloud Secrets 管理。

