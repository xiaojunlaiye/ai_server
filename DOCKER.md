# Docker 部署指南

## 快速开始

### 1. 准备环境变量
```bash
# 复制环境变量示例文件
cp env.example .env

# 编辑 .env 文件，设置你的 OpenAI API Key
vim .env
```

### 2. 构建镜像
```bash
# 构建 Docker 镜像
docker build -t llm-api .

# 或者使用 docker-compose 构建
docker-compose build
```

### 3. 运行容器

#### 方式一：直接使用 Docker
```bash
# 运行容器
docker run -d \
  --name llm-api \
  -p 8000:8000 \
  --env-file .env \
  llm-api

# 查看日志
docker logs llm-api

# 停止容器
docker stop llm-api
```

#### 方式二：使用 Docker Compose（推荐）
```bash
# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 4. 验证部署
```bash
# 检查健康状态
curl http://localhost:8000/healthz

# 查看API文档
open http://localhost:8000/docs
```

## 环境变量说明

| 变量名 | 必需 | 默认值 | 说明 |
|--------|------|--------|------|
| `OPENAI_API_KEY` | 是 | - | OpenAI API密钥 |
| `OPENAI_BASE_URL` | 否 | - | OpenAI API基础URL（用于代理） |
| `ALLOWED_ORIGINS` | 否 | 默认CORS设置 | 允许的跨域来源 |

## 生产环境建议

### 1. 使用多阶段构建优化镜像大小
```dockerfile
# 在 Dockerfile 中添加多阶段构建
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY app/ ./app/
ENV PATH=/root/.local/bin:$PATH
# ... 其余配置
```

### 2. 使用非root用户运行（已在Dockerfile中配置）

### 3. 配置资源限制
```yaml
# 在 docker-compose.yml 中添加
services:
  llm-api:
    # ... 其他配置
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
```

### 4. 使用外部配置管理
```bash
# 使用 Docker secrets 或外部配置管理工具
docker run -d \
  --name llm-api \
  -p 8000:8000 \
  --secret source=openai_key,target=/run/secrets/openai_key \
  llm-api
```

## 故障排除

### 1. 容器无法启动
```bash
# 查看容器日志
docker logs llm-api

# 检查容器状态
docker ps -a
```

### 2. API调用失败
```bash
# 检查环境变量
docker exec llm-api env | grep OPENAI

# 测试API连接
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{"model": "gpt-4o-mini", "messages": [{"role": "user", "content": "Hello"}]}'
```

### 3. 性能优化
```bash
# 监控容器资源使用
docker stats llm-api

# 调整工作进程数
docker run -d \
  --name llm-api \
  -p 8000:8000 \
  -e WORKERS=4 \
  llm-api
```
