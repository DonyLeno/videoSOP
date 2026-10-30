# Geniview v2.1 中国版

一个本地 Web 界面 + Python 服务的“视频动作分析/标注”工具，集成了 Kimi (Moonshot AI) 大模型进行视频内容分析。

## 主要特性

- **Kimi 模型支持**：默认使用 Kimi (Moonshot AI) 模型进行视频分析，支持 `kimi-2.5` 等模型。
- **视频动作分析**：选择视频，调用 AI 模型生成动作段落与建议。
- **智能标注**：生成结果 JSON 与标注视频（输出到 `result/`），包含动作时间轴、置信度等信息。
- **可视化结果**：在“结果查看”页按动作跳转播放，并展示统计图与建议。
- **批量处理**：支持视频分批次上传与分析，实时显示进度条（上传/分析两段式进度）。
- **云端历史清理**：自动清理 Kimi 云端的历史文件，节省空间。
- **Docker 部署**：提供一键部署脚本，支持离线环境。

## 目录结构

- `web/`：前端页面（入口 `web/index.html`）
- `server.py`：静态文件 + API 服务（默认监听 `8000`）
- `main.py`：核心分析逻辑，集成 Kimi API
- `data/`：输入视频目录（可在页面上传/选择）
- `result/`：输出结果目录（JSON、视频等）
- `docker/`：Docker 部署相关（Dockerfile、compose、脚本等）

## 快速开始

### 本地运行 (开发模式)

1. **安装依赖** (推荐 Python 3.11)

```bash
pip install -r requirements.txt
```

2. **启动服务**

```bash
python server.py
```

3. **访问页面**

- 打开浏览器访问: `http://localhost:8000/`

### Docker 部署 (生产环境)

我们推荐使用 Docker 进行部署，特别是针对服务器环境。

#### 1. 构建镜像 (如有修改)

```bash
# 构建 linux/amd64 镜像并导出为 tar 包
docker build --platform linux/amd64 -f docker/Dockerfile -t gemini-project:latest .
docker save -o gemini-project.tar gemini-project:latest
```

#### 2. 服务器一键部署

将以下文件上传到服务器同一目录：
- `gemini-project.tar` (镜像包)
- `docker/docker-compose.yml` (编排文件)
- `docker/deploy.sh` (部署脚本)

运行部署脚本：

```bash
chmod +x docker/deploy.sh
./docker/deploy.sh
```

服务将默认运行在 `8000` 端口。

## API Key 配置

页面“视觉检测任务”里可以输入 API Key：

- **Kimi API Key**：支持 Moonshot AI 的 API Key。
- **存储方式**：浏览器侧会保存到 localStorage；点击“更新系统 Key”会写入服务端 `.env` 文件。
- **环境变量**：也可通过环境变量 `MOONSHOT_API_KEY` 或 `GEMINI_API_KEY` 提供。

## 注意事项

- **视频上传**：支持大文件上传，前端会自动处理 Token 过期等问题。
- **数据持久化**：Docker 部署模式下，`data/` 和 `result/` 目录会自动挂载到宿主机，保证数据不丢失。
- **MySQL**：项目内置 MySQL (MariaDB) 用于用户管理，默认账号 `admin` / `geniviewa`。

## 版本历史

- **v2.1 中国版**：
    - 全面集成 Kimi (Moonshot AI) 模型。
    - 优化 Docker 部署流程，支持离线镜像包。
    - 改进前端进度条显示逻辑，更精准反映分析进度。
    - 修复大批量日志导致的页面卡顿问题。
    - 增加 Kimi 云端文件自动清理功能。
