# 1688 以图搜货 API

> 支持 1688、淘宝、阿里巴巴国际站、义乌购的以图搜货功能
> 可部署为 API 服务，支持 Docker 部署

## 功能特性

- ✅ 1688 以图搜货（自动获取产品链接）
- ✅ 淘宝以图搜货
- ✅ 阿里巴巴国际站以图搜货
- ✅ 义乌购以图搜货
- ✅ 支持代理 IP 池（防止反爬）
- ✅ FastAPI 接口服务
- ✅ Docker 部署

## 快速开始

### 安装依赖

```bash
# 使用 uv
uv sync
uv run playwright install chromium
```

### 命令行使用

```bash
uv run python main.py
```

### 启动 API 服务

```bash
uv run uvicorn api:app --host 0.0.0.0 --port 8000
```

API 文档：http://localhost:8000/docs

### API 接口

#### 上传图片搜索

```bash
curl -X POST "http://localhost:8000/search/upload" \
  -F "file=@your_image.jpg" \
  -F "limit=5"
```

#### 通过 URL 搜索

```bash
curl "http://localhost:8000/search/url?image_url=https://example.com/image.jpg&limit=5"
```

#### 返回示例

```json
{
  "success": true,
  "image_id": "1234567890",
  "search_url": "https://s.1688.com/youyuan/index.htm?...",
  "products": [
    {
      "title": "产品标题",
      "url": "https://detail.1688.com/offer/123456.html",
      "offer_id": "123456"
    }
  ]
}
```

## 代理配置

编辑 `config/proxy_config.py`：

```python
# 是否启用代理
PROXY_ENABLED = True  # 改为 True 启用代理

# 代理 API Key
PROXY_API_KEY = "你的API Key"

# 如果代理需要用户名密码认证
PROXY_USERNAME = ""
PROXY_PASSWORD = ""
```

**注意**：如果代理服务需要 IP 白名单认证，请在代理服务商后台添加你的服务器 IP。

## Docker 部署

### 构建镜像

```bash
docker build -t 1688-crawler .
```

### 运行容器

```bash
docker run -d -p 8000:8000 --name 1688-crawler 1688-crawler
```

### 使用 docker-compose

```bash
docker-compose up -d
```

## 项目结构

```
├── api.py                 # FastAPI 服务
├── main.py                # 命令行入口
├── config/
│   ├── setting.py         # API 配置
│   └── proxy_config.py    # 代理配置
├── lib/
│   ├── proxy.py           # 代理 IP 池
│   ├── func_txy.py        # 工具函数
│   ├── ali1688/           # 1688 模块
│   ├── world_taobao/      # 淘宝模块
│   ├── alibaba.py         # 阿里巴巴国际站
│   └── yiwugo.py          # 义乌购
├── Dockerfile
└── docker-compose.yml
```

## 注意事项

1. 首次运行需要安装 Playwright 浏览器：`uv run playwright install chromium`
2. Docker 部署时会自动安装浏览器依赖
3. 建议部署到服务器后启用代理，避免被反爬
4. 代理 API 有请求频率限制（60次/分钟）

## License

MIT - 仅供学习，禁止商用
