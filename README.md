# Gemini Video Analysis

一个本地 Web 界面 + Python 服务的“视频动作分析/标注”工具：

- 选择视频，调用 Gemini 模型生成动作段落与建议
- 生成结果 JSON 与标注视频（输出到 `result/`）
- 在“结果查看”页按动作跳转播放，并展示统计图与建议

默认服务端口：`8000`（Docker/Compose 可映射到任意宿主机端口，当前 compose 默认映射到 `8008`）

## 目录结构

- `web/`：前端页面（入口 `web/index.html`）
- `server.py`：静态文件 + API 服务（默认监听 `8000`）
- `data/`：输入视频目录（可在页面上传/选择）
- `result/`：输出结果目录（JSON、视频等）

## 本地运行

1) 安装依赖（建议 Python 3.11）

```bash
pip install -r requirements.txt
```

2) 启动服务

```bash
python server.py
```

3) 打开页面

- http://localhost:8000/

## API Key 配置

页面“视觉检测任务”里可以输入 API Key：

- 浏览器侧会保存到 localStorage
- 点击“更新系统 Key”会把 Key 写入服务端工作目录的 `.env`（`server.py` 启动时会读取）

如果你在 Docker 中运行，推荐通过环境变量或挂载 `.env` 方式提供 Key：

- 环境变量：`GOOGLE_API_KEY`（服务端会读取）
- 或将宿主机的 `.env` 挂载到容器 `/app/.env`

## Docker（构建 amd64 镜像并导出 tar）

在本机（例如 macOS）构建 linux/amd64 镜像并导出 tar 包：

```bash
docker buildx build --platform linux/amd64 -t gemini-video-analysis:amd64 --load .
docker save gemini-video-analysis:amd64 -o gemini-video-analysis_amd64.tar
```

生成文件：`gemini-video-analysis_amd64.tar`（在项目根目录）

备注：如果所在网络无法访问 Docker Hub，可在构建时指定可用的 Python 镜像源：

```bash
docker buildx build --platform linux/amd64 \
  -t gemini-video-analysis:amd64 \
  --build-arg PYTHON_BASE_IMAGE=m.daocloud.io/docker.io/library/python:3.11-slim \
  --load .
```

## 服务器离线部署（使用 tar + docker compose）

### 1) 拷贝文件到服务器

把以下文件上传到服务器同一目录（例如 `/home/visionView`）：

- `gemini-video-analysis_amd64.tar`
- `docker-compose.yml`
- （可选）`data/`、`result/` 目录（用于持久化）

### 2) 导入镜像

```bash
docker load -i gemini-video-analysis_amd64.tar
```

### 3) 一键启动

```bash
docker compose up -d
```

`docker-compose.yml` 默认映射宿主机端口 `8008 -> 容器 8000`，访问：

- `http://<服务器IP>:8008/`

### 4) 自定义对外端口

```bash
HOST_PORT=9000 docker compose up -d
```

访问：

- `http://<服务器IP>:9000/`

## 常见问题

### docker compose 报 “no such file or directory: Dockerfile”

这是因为远端目录里只有 `docker-compose.yml`，但 compose 配置里包含 `build` 指令会尝试构建镜像。推荐流程是：

1. 本地构建并导出 tar
2. 服务器 `docker load`
3. 服务器 `docker compose up -d`

