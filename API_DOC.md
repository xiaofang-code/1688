# 📬 1688 以图搜货 - 批量处理 API 文档

## 基本信息

| 项目 | 说明 |
|------|------|
| 接口地址 | `POST /batch/email` |
| 功能 | 批量图片搜索，结果通过邮件发送 Excel |
| 最大数量 | 3000 张图片 |
| 处理方式 | 异步（立即返回，后台处理） |

---

## API 端点

### 1. 批量搜索 + 邮件通知

**请求**
```
POST /batch/email
Content-Type: application/json
```

**请求体**
```json
{
  "image_urls": ["图片URL1", "图片URL2", ...],
  "email": "your@email.com",
  "limit": 5
}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `image_urls` | `string[]` | ✅ | 图片 URL 列表（1-3000个） |
| `email` | `string` | ✅ | 结果发送到的邮箱地址 |
| `limit` | `int` | ❌ | 每张图片返回的产品数量（默认 5，最大 20） |

**响应示例**
```json
{
  "task_id": "9d67a1ac-f98e-4751-9995-3e9416e4179b",
  "status": "pending",
  "total": 100,
  "email": "your@email.com",
  "message": "任务已提交！处理完成后结果将发送到 your@email.com",
  "estimated_time": "约 11 - 22 分钟"
}
```

---

### 2. 查询任务状态

**请求**
```
GET /batch/status/{task_id}
```

**响应示例**
```json
{
  "task_id": "9d67a1ac-f98e-4751-9995-3e9416e4179b",
  "status": "completed",
  "total": 100,
  "completed": 100,
  "success_count": 98,
  "fail_count": 2,
  "progress": "100/100",
  "email": "your@email.com",
  "message": "结果已发送到 your@email.com",
  "duration": 320.5,
  "created_at": "2025-11-28T15:19:27.927641"
}
```

**状态说明**

| status | 说明 |
|--------|------|
| `pending` | 等待处理 |
| `processing` | 正在处理中 |
| `completed` | 处理完成，邮件已发送 |
| `email_failed` | 处理完成，但邮件发送失败 |

---

### 3. 单张图片搜索（上传文件）

**请求**
```
POST /search/upload
Content-Type: multipart/form-data
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | `file` | ✅ | 图片文件 |
| `limit` | `int` | ❌ | 返回产品数量（默认 5，最大 20） |

**响应示例**
```json
{
  "success": true,
  "image_id": "1087708630684325260",
  "search_url": "https://s.1688.com/youyuan/index.htm?tab=imageSearch&imageId=...",
  "products": [
    {
      "title": "产品标题",
      "url": "https://detail.1688.com/offer/123456.html",
      "offer_id": "123456"
    }
  ],
  "error": null
}
```

---

### 4. 单张图片搜索（URL）

**请求**
```
GET /search/url?image_url={url}&limit={limit}
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `image_url` | `string` | ✅ | 图片 URL |
| `limit` | `int` | ❌ | 返回产品数量（默认 5，最大 20） |

---

### 5. 健康检查

**请求**
```
GET /health
```

**响应**
```json
{
  "status": "healthy",
  "active_tasks": 2
}
```

---

## Excel 输出格式

邮件附件 Excel 包含以下列：

| 序号 | 原图URL | 状态 | 产品链接 |
|------|---------|------|----------|
| 1 | https://xxx.jpg | 成功 | https://detail.1688.com/offer/123.html,https://... |
| 2 | https://yyy.jpg | 失败: 超时 | |

- **产品链接**：5 个链接用逗号分隔

---

## 使用示例

### 1️⃣ cURL

```bash
# 批量搜索
curl -X POST "http://your-server:8688/batch/email" \
  -H "Content-Type: application/json" \
  -d '{
    "image_urls": [
      "https://example.com/image1.jpg",
      "https://example.com/image2.jpg",
      "https://example.com/image3.jpg"
    ],
    "email": "your@email.com",
    "limit": 5
  }'

# 查询状态
curl "http://your-server:8688/batch/status/9d67a1ac-f98e-4751-9995-3e9416e4179b"
```

### 2️⃣ Python

```python
import requests

# 批量搜索
data = {
    "image_urls": [
        "https://example.com/image1.jpg",
        "https://example.com/image2.jpg"
    ],
    "email": "your@email.com",
    "limit": 5
}

response = requests.post("http://your-server:8688/batch/email", json=data)
result = response.json()
print(f"任务ID: {result['task_id']}")
print(f"预计时间: {result['estimated_time']}")

# 查询状态
task_id = result['task_id']
status = requests.get(f"http://your-server:8688/batch/status/{task_id}")
print(status.json())
```

### 3️⃣ Google Apps Script

```javascript
function batchSearch() {
  // 从 A 列读取图片 URL（从第 2 行开始，跳过表头）
  var sheet = SpreadsheetApp.getActiveSheet();
  var lastRow = sheet.getLastRow();
  var range = sheet.getRange("A2:A" + lastRow);
  var values = range.getValues();
  
  // 过滤空值
  var imageUrls = values.flat().filter(function(url) {
    return url !== "";
  });
  
  if (imageUrls.length === 0) {
    SpreadsheetApp.getUi().alert("A 列没有找到图片 URL");
    return;
  }
  
  var payload = {
    "image_urls": imageUrls,
    "email": "your@email.com",  // 修改为你的邮箱
    "limit": 5
  };
  
  var options = {
    "method": "post",
    "contentType": "application/json",
    "payload": JSON.stringify(payload),
    "muteHttpExceptions": true
  };
  
  try {
    var response = UrlFetchApp.fetch("http://your-server:8688/batch/email", options);
    var result = JSON.parse(response.getContentText());
    
    SpreadsheetApp.getUi().alert(
      "✅ 任务已提交！\n\n" +
      "任务ID: " + result.task_id + "\n" +
      "图片数量: " + result.total + "\n" +
      "预计时间: " + result.estimated_time + "\n\n" +
      "处理完成后结果将发送到: " + result.email
    );
  } catch (e) {
    SpreadsheetApp.getUi().alert("❌ 请求失败: " + e.message);
  }
}

// 添加自定义菜单
function onOpen() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu('1688 搜索')
    .addItem('批量搜索', 'batchSearch')
    .addToUi();
}
```

### 4️⃣ JavaScript (Fetch)

```javascript
async function batchSearch(imageUrls, email) {
  const response = await fetch('http://your-server:8688/batch/email', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      image_urls: imageUrls,
      email: email,
      limit: 5
    })
  });
  
  const result = await response.json();
  console.log('任务ID:', result.task_id);
  return result;
}

// 使用示例
batchSearch([
  'https://example.com/image1.jpg',
  'https://example.com/image2.jpg'
], 'your@email.com');
```

---

## ⚡ 性能参数

| 参数 | 值 |
|------|-----|
| 并发数 | 3（同时处理 3 张图片） |
| 单张耗时 | 约 5-10 秒 |
| 代理策略 | 每张图片使用不同 IP |
| 最大批量 | 3000 张 |
| 重试次数 | 2 次 |

**预估时间计算：**
```
处理时间 ≈ (图片数量 × 10秒) / 3并发 / 60秒
```

| 图片数量 | 预估时间 |
|----------|----------|
| 10 张 | 约 30 秒 |
| 100 张 | 约 5-10 分钟 |
| 500 张 | 约 25-50 分钟 |
| 1000 张 | 约 50-100 分钟 |
| 3000 张 | 约 2.5-5 小时 |

---

## 📌 注意事项

1. **邮箱格式**：必须是有效的邮箱地址（支持 Gmail、QQ、163 等）
2. **图片 URL**：必须是可直接访问的图片链接（http/https）
3. **图片格式**：支持 JPG、PNG、WebP 等常见格式
4. **超时处理**：单张图片超时会自动切换代理重试 2 次
5. **代理 IP**：批量处理时会自动获取多个代理 IP，避免被 1688 封禁
6. **结果保存**：任务状态保存在服务器内存中，服务重启后会丢失
7. **并发限制**：建议单次提交不超过 1000 张，分批提交效果更好

---

## 🔧 部署说明

### Docker 部署

```bash
# 构建镜像
docker build -t 1688-api .

# 运行容器
docker run -d -p 8688:8688 --name 1688-api 1688-api
```

### Docker Compose

```bash
docker-compose up -d
```

### 本地运行

```bash
# 安装依赖
uv sync

# 安装浏览器
uv run playwright install chromium

# 启动服务
uv run uvicorn api:app --host 0.0.0.0 --port 8688
```

---

## 📞 API 交互文档

启动服务后访问：
- Swagger UI: `http://your-server:8688/docs`
- ReDoc: `http://your-server:8688/redoc`

