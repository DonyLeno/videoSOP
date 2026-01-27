MySQL 容器内访问应使用 127.0.0.1 并确保 root 为密码认证（避免 localhost 触发 socket 认证导致 1698）
Python 依赖包中 NumPy 应限制版本为 < 2.0.0，以避免与 Ultralytics/PyTorch 等预编译库发生兼容性冲突导致运行时崩溃。
