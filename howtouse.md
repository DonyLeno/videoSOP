# 云服务器一键部署说明

## 需要上传的文件

- gemini-video-analysis_amd64.tar
- docker-compose.yml

建议将以上两个文件放到同一个目录。

## 在云服务器上执行的命令

```bash
docker load -i gemini-video-analysis_amd64.tar
docker compose up -d
```

## 访问地址

- 默认端口：8008
- 访问地址：http://<服务器公网IP>:8008/

如需修改端口，可设置环境变量 HOST_PORT，例如：

```bash
HOST_PORT=9000 docker compose up -d
```
