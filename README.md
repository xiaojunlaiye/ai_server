# LLM_api Demo

/root/LLM_api/
├── app/                          # FastAPI 后端应用
│   ├── main.py                   # 主应用入口，包含聊天接口
│   ├── common/                   # 公共模块
│   │   └── openai_client.py     # OpenAI 客户端封装
│   ├── routers/                  # API 路由层
│   │   ├── translation.py       # 翻译服务路由
│   │   ├── xhs_hotpost.py       # 小红书爆款文案路由
│   │   └── image_gen.py         # 图片生成路由
│   └── services/                 # 业务逻辑层
│       ├── translation.py       # 翻译服务实现
│       ├── xhs_hotpost.py       # 小红书文案生成实现
│       └── image_gen.py         # 图片生成实现
├── flutter_client/               # Flutter 客户端
│   ├── lib/main.dart            # Flutter 主应用
│   └── pubspec.yaml             # Flutter 依赖配置
├── requirements.txt             # Python 依赖
└── README.md                    # 项目文档

后端：FastAPI（Python）代理到 OpenAI。
客户端：Flutter 示例。

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
- OPENAI_BASE_URL：兼容网关/代理的基础地址
- ALLOWED_ORIGINS：CORS 允许来源（逗号分隔）

### 4) 运行服务
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

打开接口文档：http://localhost:8000/docs

### 5) 聊天（兼容 Responses/Chat Completions）示例
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

## 二、翻译服务（Translation）

- 路径：`POST /translation/translate`
- 请求体：
  - `text`：待翻译文本（必填）
  - `target_lang`：目标语言（必填，如 `English` / `中文` / `Japanese`）
  - `source_lang`：源语言（可选，留空则自动检测）
  - `model`、`temperature`、`max_tokens`、`extra`：同 OpenAI 参数

示例：
```bash
curl -X POST http://localhost:8000/translation/translate \
  -H 'Content-Type: application/json' \
  -d '{
    "text": "今天天气不错，我们去公园散步吧。",
    "target_lang": "English"
  }'
```

## 三、小红书爆款服务（XHS Hotpost）

- 路径：`POST /xhs/hotpost`
- 请求体：
  - `topic`（必填）
  - `audience`、`style`（可选）
  - 其他与 OpenAI 相关的可选参数同上

示例：
```bash
curl -X POST http://localhost:8000/xhs/hotpost \
  -H 'Content-Type: application/json' \
  -d '{
    "topic": "夏日防晒霜推荐",
    "audience": "学生党",
    "style": "真实、种草"
  }'
```

## 四、图片生成服务（Images）

- 路径：`POST /images/generate`
- 请求体：
  - `prompt`（必填）
  - `model`（可选，默认 `gpt-image-1` 或兼容）
  - `size`（如 `1024x1024`）`quality`、`n` 等（可选）

示例：
```bash
curl -X POST http://localhost:8000/images/generate \
  -H 'Content-Type: application/json' \
  -d '{
    "prompt": "A cute corgi playing skateboard, cartoon style",
    "size": "512x512"
  }'
```

注意：当前实现返回 URL 或 base64（取决于上游），SDK 不支持 Images API 时会报错提示。

## 五、Flutter 客户端

见 `flutter_client/lib/main.dart`，默认请求 `http://localhost:8000/chat`。可按需增加翻译、XHS、图片生成的调用逻辑。
