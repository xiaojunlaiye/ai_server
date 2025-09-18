# LLM_api Demo

后端：FastAPI（Python）代理到 OpenAI Chat Completions。
客户端：Flutter 示例，调用后端的 /chat。

## 一、后端（FastAPI）

### 1) 可选：创建虚拟环境
```bash
python3 -m venv .venv && source .venv/bin/activate
```

### 2) 安装依赖
```bash
pip install -r requirements.txt
```

### 3) 配置环境变量
复制 `.env.example` 为 `.env` 并填写：
```bash
cp .env.example .env
# 然后编辑 .env 设置 OPENAI_API_KEY
```
必须：
- OPENAI_API_KEY：你的 OpenAI API Key

可选：
- OPENAI_BASE_URL：如果使用兼容网关/代理可覆盖基础地址
- ALLOWED_ORIGINS：CORS 允许的来源（逗号分隔），默认放开常见本地地址

### 4) 运行服务
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
打开接口文档：http://localhost:8000/docs

### 5) 示例请求
```bash
curl -X POST http://localhost:8000/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-4o-mini",
    "messages": [
      {"role": "user", "content": "你好，帮我写个示例。"}
    ]
  }'
```

## 二、Flutter 客户端

我们在 `flutter_client/lib/main.dart` 提供了一个最小示例，默认请求 `http://localhost:8000/chat`。

快速开始：
1. 创建项目（如无）：`flutter create flutter_client`
2. 用本仓库的 `flutter_client/lib/main.dart` 覆盖生成的同名文件
3. 在 `flutter_client/pubspec.yaml` 添加依赖：
   ```yaml
   dependencies:
     flutter:
       sdk: flutter
     http: ^1.2.2
   ```
4. 运行：`cd flutter_client && flutter run`

如果后端运行在设备外部或不同端口，请在 `main.dart` 中修改 `backendBaseUrl`。

## 说明
- 示例为非流式返回，后续可扩展为流式（SSE）。
- 请求/响应格式尽量保持 OpenAI Chat Completions 的习惯用法。
