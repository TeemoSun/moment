FROM python:3.11-slim

# 放在 RUN apt-get update 之前
RUN echo 'deb https://mirrors.aliyun.com/debian/ bookworm main contrib non-free' > /etc/apt/sources.list && \
    echo 'deb https://mirrors.aliyun.com/debian-security/ bookworm-security main contrib non-free' >> /etc/apt/sources.list && \
    echo 'deb https://mirrors.aliyun.com/debian/ bookworm-updates main contrib non-free' >> /etc/apt/sources.list

# 系统依赖
RUN apt-get update && \
    apt-get install -y --no-install-recommends supervisor && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 先写入 pip 配置文件
RUN mkdir -p /root/.pip && \
    echo "[global]\nindex-url = https://mirrors.aliyun.com/pypi/simple/\ntrusted-host = mirrors.aliyun.com" > /root/.pip/pip.conf

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 拷贝源码
COPY . .

# 创建上传目录并放宽权限
RUN mkdir -p /app/static/uploads && \
    chmod -R 777 /app/static/uploads

EXPOSE 5000

# 默认执行 app.py
CMD ["python", "app.py"]