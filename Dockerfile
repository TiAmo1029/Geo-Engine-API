# 使用一个官方的、轻量的Python 3.10镜像作为基础
FROM python:3.10-slim-bullseye

# 设置工作目录
WORKDIR /app

# 复制需求文件
COPY requirements.txt .

# 安装所有Python依赖
# 这次，pip安装的所有东西（库和可执行文件）都会留在最终的镜像里
RUN pip install --no-cache-dir --default-timeout=100 -r requirements.txt

# 复制我们自己的应用代码
COPY . .

# 暴露8000端口
EXPOSE 8000

# 定义容器启动时要执行的命令
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]