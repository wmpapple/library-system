# frontend/Dockerfile
FROM node:16-alpine

WORKDIR /app

# 复制依赖描述文件
COPY package*.json ./

# 安装依赖 (使用淘宝源加速)
RUN npm install --registry=https://registry.npmmirror.com

# 复制前端所有代码
COPY . .

# 暴露端口 (假设你前端运行在 8080 或 8081，请根据你的实际情况修改)
EXPOSE 8080

# 启动开发服务器
CMD ["npm", "run", "serve"]