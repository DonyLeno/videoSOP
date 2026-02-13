# Version History

## v10.6.5
- **Date**: 2026-02-13
- **Commit Message**: 避免 Debian pip/ wheel 卸载冲突，确保 Docker 可安装依赖并导出 tar

## v10.6.4
- **Date**: 2026-02-13
- **Commit Message**: 修复 Debian pip 升级冲突，确保 Docker 构建可继续安装依赖并导出 tar

## v10.6.3
- **Date**: 2026-02-13
- **Commit Message**: 修复 mariadb:11 基础镜像下 pip PEP668 安装失败，确保可构建 amd64 tar 包

## v10.6.2
- **Date**: 2026-02-13
- **Commit Message**: 支持通过镜像源构建（避免 DockerHub 超时），并导出 amd64 tar 包

## v10.6.1
- **Date**: 2026-02-13
- **Commit Message**: 修复特殊字符结果视频无法播放；修复 SOP 下载与导出兼容性；优化 Docker/DB 启动稳定性

## v10.6
- **Date**: 2026-02-11
- **Commit Message**: 重构工程结构（backend/、docker/、docs/）并整理部署脚本

## v10.52
- **Date**: 2026-02-11
- **Commit Message**: 修复 /api/analyze 中 shutil 作用域导致的 UnboundLocalError

## v10.51
- **Date**: 2026-02-11
- **Commit Message**: 修复 SOP 打包下载在云端无响应；SOP 文件夹命名为 SOP1/SOP2

## v10.0
- **Date**: 2026-02-10
- **Commit Message**: SOP视频分拆

## v2.3
- **Date**: 2026-02-02
- **Commit Message**: prompt changing

## v2.2
- **Date**: 2026-02-01
- **Commit Message**: chinese version fix chinese name input bug
