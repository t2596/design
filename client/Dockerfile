# 车辆客户端 Docker 镜像
# 注意：此 Dockerfile 必须从项目根目录构建
# 构建命令：docker build -f client/Dockerfile -t vehicle-client:latest .

FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制源代码
COPY src/ ./src/
COPY config/ ./config/
COPY client/ ./client/

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV GATEWAY_HOST=gateway
ENV GATEWAY_PORT=8000

# 暴露端口（如果需要）
# EXPOSE 9000

# 设置入口点
ENTRYPOINT ["python", "client/vehicle_client.py"]

# 默认参数
CMD ["--mode", "continuous", "--interval", "10"]
