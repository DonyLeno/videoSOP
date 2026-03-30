# Version History

## v2.5
- **Date**: 2026-03-30
- **Commit Message**: 修复 Dockerfile 遗漏 dashscope 导致 Qwen 报错的问题

## v2.4
- **Date**: 2026-03-30
- **Commit Message**: 增加 qwen 模型适配，修复 admin 登录 401 竞态问题，优化进度显示

## v2.3
- **Date**: 2026-03-03
- **Commit Message**: 英文模式下检测完成后自动调用新版翻译，输出完整英文结果

## v2.2
- **Date**: 2026-03-03
- **Commit Message**: 修复英文结果时间段解析导致的时间轴缺失，并优化时间轴颜色与跨域请求头

## v2.1
- **Date**: 2026-02-28
- **Commit Message**: 新增动作编辑时间校验逻辑，确保动作时间合法且连贯

## v2.0
- **Date**: 2026-02-27
- **Commit Message**: 启动新版本机制：统一 APP_VERSION，前端编辑弹窗与多语言修复

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
