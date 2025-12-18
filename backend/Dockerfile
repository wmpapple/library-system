# backend/Dockerfile
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 先复制依赖文件（为了利用缓存加速构建）
COPY requirements.txt .

# 安装依赖 (使用了清华源加速)
RUN pip install --no-cache-dir -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 复制所有代码
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]