# PDF 翻译 Web 工具

> 基于 AI 的智能 PDF 文档翻译工具，支持 Web 界面和 API 接口，保持文档结构不变

![License](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.10+-blue.svg)
![FastAPI](https://img.shields.io/badge/fastapi-0.116+-green.svg)
![Gradio](https://img.shields.io/badge/gradio-5.34+-orange.svg)
![Docker](https://img.shields.io/badge/docker-latest-blue.svg)

---

## 项目介绍

PDF 翻译 Web 工具是一个专业的 AI 驱动 PDF 文档翻译服务，基于 BabelDOC 翻译引擎，支持 OpenAI/DeepSeek 等大语言模型，提供 RESTful API 和 Gradio Web 界面两种使用方式，翻译后保持原始 PDF 文档结构和布局不变。

### 核心特性

- **智能翻译**: 基于 OpenAI/DeepSeek 等大语言模型的高质量翻译
- **保持格式**: 翻译后保持原始 PDF 文档结构、布局和样式
- **双重接口**: FastAPI REST API + Gradio Web 界面
- **灵活配置**: 通过环境变量灵活配置翻译参数
- **容器部署**: Docker/Docker Compose 一键部署
- **实时监控**: 翻译进度实时跟踪和状态查询
- **多种输出**: 支持单语 PDF、双语 PDF、纯文本等多种输出格式
- **批量处理**: 支持批量上传和翻译多个 PDF 文件
- **uv 包管理**: 支持超快的 uv 包管理器，比 pip 快 10-100 倍

---

## 功能清单

| 功能名称 | 功能说明 | 技术栈 | 状态 |
|---------|---------|--------|------|
| 智能翻译 | 基于 LLM 的高质量翻译 | BabelDOC + OpenAI | ✅ 稳定 |
| 保持格式 | 保持 PDF 结构和布局 | PDF 处理引擎 | ✅ 稳定 |
| REST API | 标准化 API 接口 | FastAPI 0.116+ | ✅ 稳定 |
| Web 界面 | 可视化操作界面 | Gradio 5.34+ | ✅ 稳定 |
| 环境配置 | 灵活的配置管理 | python-dotenv | ✅ 稳定 |
| Docker 部署 | 容器化一键部署 | Docker + Compose | ✅ 稳定 |
| 实时监控 | 翻译进度跟踪 | FastAPI WebSocket | ✅ 稳定 |
| 多种输出 | 单语/双语/纯文本 | BabelDOC | ✅ 稳定 |
| 批量处理 | 批量上传翻译 | FastAPI | ✅ 稳定 |
| uv 包管理 | 超快依赖安装 | uv | ✅ 稳定 |

---

## 技术架构

| 技术 | 版本 | 用途 |
|------|------|------|
| Python | 3.10+ | 主要开发语言 |
| BabelDOC | latest | PDF 翻译引擎 |
| FastAPI | 0.116+ | Web 框架 |
| Gradio | 5.34+ | Web UI 框架 |
| Uvicorn | 0.35+ | ASGI 服务器 |
| httpx | 0.27+ | 异步 HTTP 客户端 |
| Pillow | 11.3+ | 图片处理 |

### 系统架构

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                            系统架构图                                            │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│   ┌──────────────────┐       ┌─────────────────────────┐       ┌─────────────┐ │
│   │  Gradio Web UI   │ ◄────► │   FastAPI Backend      │ ◄────► │  OpenAI API │ │
│   │   端口 7860       │       │   端口 8000             │       │  (翻译引擎)  │ │
│   └──────────────────┘       └─────────────────────────┘       └─────────────┘ │
│           │                            │                              │        │
│           ▼                            ▼                              ▼        │
│   Web 可视化界面            API 接口 + 文件处理              BabelDOC 翻译    │
│   上传 PDF / 下载结果        任务队列 / 状态查询              智能翻译引擎      │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 安装说明

### 环境要求

- Python 3.10+ (< 3.14)
- pip 包管理器或 uv 包管理器（推荐）
- Docker / Docker Compose（可选）

### 安装依赖

**方式一：使用 uv 包管理器（推荐）**

```bash
# 安装 uv（如果没有安装）
curl -LsSf https://astral.sh/uv/install.sh | sh
# 或使用 pip 安装
pip install uv

# 使用 uv 安装依赖（自动创建虚拟环境）
uv sync
```

**方式二：使用传统 pip**

```bash
# 安装依赖
pip install -e .
```

---

## 使用说明

### 1. 配置环境变量

复制环境变量模板并编辑：

```bash
cp .env.example .env
```

编辑 `.env` 文件，设置 API 密钥：

```bash
# OpenAI 配置（必填）
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=deepseek-ai/DeepSeek-V3
OPENAI_BASE_URL=https://api.siliconflow.cn/v1

# 翻译配置
QPS=4
DEFAULT_LANG_IN=en
DEFAULT_LANG_OUT=zh
WATERMARK_OUTPUT_MODE=no_watermark
```

### 2. 启动服务

**方式一：启动 API 服务器**

```bash
# 使用 uv（推荐）
uv run python scripts/run_server.py --host 0.0.0.0 --port 8000

# 或使用传统方式
python scripts/run_server.py --host 0.0.0.0 --port 8000
```

API 服务将在 `http://localhost:8000` 启动，文档地址：`http://localhost:8000/docs`

**方式二：启动 Web 界面**

```bash
# 使用 uv（推荐）
uv run python scripts/run_gradio.py --server-url http://localhost:8000 --port 7860

# 或使用传统方式
python scripts/run_gradio.py --server-url http://localhost:8000 --port 7860
```

Web 界面将在 `http://localhost:7860` 启动

### 3. 使用方法

**API 使用示例**

```python
from pdftranslate_web.api_client import BabelDOCClient

# 创建客户端
client = BabelDOCClient("http://localhost:8000")

# 翻译 PDF 文件
downloaded_files = client.translate_and_download(
    pdf_path="document.pdf",
    output_dir="./output",
    lang_in="en",
    lang_out="zh"
)

print(f"翻译完成：{downloaded_files}")
```

**命令行使用**

```bash
# 使用 API 客户端
uv run python src/pdftranslate_web/api_client.py document.pdf --output-dir ./output --lang-out zh

# 检查服务器状态
curl http://localhost:8000/health
```

**Web 界面使用**

1. 打开浏览器访问 `http://localhost:7860`
2. 上传 PDF 文件
3. 选择翻译选项（源语言、目标语言、输出类型）
4. 点击"开始翻译"
5. 等待翻译完成并下载结果

---

## 配置说明

### 环境变量配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `OPENAI_API_KEY` | OpenAI API 密钥 | 无（必填） |
| `OPENAI_MODEL` | 使用的模型 | `deepseek-ai/DeepSeek-V3` |
| `OPENAI_BASE_URL` | API 端点 | `https://api.siliconflow.cn/v1` |
| `SERVER_HOST` | 服务器地址 | `0.0.0.0` |
| `SERVER_PORT` | 服务器端口 | `8000` |
| `QPS` | 请求频率限制 | `4` |
| `DEFAULT_LANG_IN` | 默认源语言 | `en` |
| `DEFAULT_LANG_OUT` | 默认目标语言 | `zh` |
| `WATERMARK_OUTPUT_MODE` | 水印模式 | `no_watermark` |
| `NO_DUAL` | 是否生成双语 PDF | `false` |
| `NO_MONO` | 是否生成单语 PDF | `false` |

### API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/translate` | 提交翻译任务 |
| GET | `/status/{task_id}` | 查询翻译状态 |
| GET | `/download/{task_id}/{file_type}` | 下载翻译结果 |
| GET | `/health` | 健康检查 |

详细 API 文档请访问：`http://localhost:8000/docs`

---

## 项目结构

```
pdftranslate_web/
├── src/pdftranslate_web/       # 核心模块
│   ├── __init__.py
│   ├── api_server.py          # FastAPI API 服务器
│   ├── api_client.py          # Python 客户端 SDK
│   └── gradio_client.py       # Gradio Web 界面
├── scripts/                   # 启动脚本
│   ├── run_server.py         # 启动 API 服务器
│   └── run_gradio.py         # 启动 Web 界面
├── docker/                   # Docker 配置
│   └── start.sh             # 容器启动脚本
├── docs/                     # 文档
│   ├── API_USAGE.md         # API 使用说明
│   └── GRADIO_USAGE.md      # Web 界面使用说明
├── tests/                    # 测试文件
├── .env.example             # 环境变量配置模板
├── docker-compose.yml       # Docker Compose 配置
├── Dockerfile              # Docker 镜像配置
├── pyproject.toml           # 项目配置和依赖
└── README.md               # 项目说明
```

---

## 开发指南

### 本地开发

```bash
# 克隆项目
git clone https://github.com/wwwzhouhui/pdftranslate_web
cd pdftranslate_web

# 方式一：使用 uv（推荐）
# 安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装开发依赖
uv sync --dev

# 方式二：使用传统 pip + 虚拟环境
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 安装开发依赖
pip install -e ".[dev]"
```

### 运行测试

```bash
pytest tests/
```

### 代码格式化

```bash
black src/
isort src/
```

---

## Docker 部署

### 使用 Docker Compose（推荐）

```bash
# 1. 配置环境变量
cp .env.example .env
nano .env  # 编辑环境变量

# 2. 构建并启动服务
docker-compose up -d

# 3. 查看服务状态
docker-compose ps

# 4. 查看日志
docker-compose logs -f pdftranslate

# 5. 停止服务
docker-compose down
```

服务启动后访问：
- API 服务：http://localhost:8000
- Web 界面：http://localhost:7860
- API 文档：http://localhost:8000/docs

### 使用 Docker 命令

```bash
# 构建镜像
docker build -t pdftranslate_web .

# 运行容器
docker run -d \
  --name pdftranslate \
  -p 8000:8000 \
  -p 7860:7860 \
  -e OPENAI_API_KEY="your-api-key" \
  pdftranslate_web

# 查看日志
docker logs -f pdftranslate

# 停止容器
docker stop pdftranslate
```

---

## 常见问题

<details>
<summary>Q: API 密钥错误？</summary>

A: 检查以下几点：
1. 确认 `.env` 文件中的 `OPENAI_API_KEY` 设置正确
2. 确认 API 密钥有效且有足够配额
3. 检查 `OPENAI_BASE_URL` 是否正确
4. 确认网络连接正常，可以访问 API 服务
</details>

<details>
<summary>Q: 模块导入错误？</summary>

A:
1. 确保已正确安装项目依赖：`uv sync` 或 `pip install -e .`
2. 检查 Python 路径设置
3. 确认使用正确的虚拟环境
4. 尝试重新安装依赖：`uv sync --reinstall`
</details>

<details>
<summary>Q: 端口被占用？</summary>

A:
1. 修改 `.env` 文件中的端口号（SERVER_PORT）
2. 或在启动命令中指定其他端口：`--port 8001`
3. 检查并释放占用端口的进程：`lsof -i :8000`
</details>

<details>
<summary>Q: 翻译失败？</summary>

A:
1. 检查网络连接是否正常
2. 确认 API 服务可用性
3. 查看日志文件获取详细错误信息
4. 检查 PDF 文件是否损坏或格式不支持
5. 尝试降低 QPS 值减少并发请求
</details>

<details>
<summary>Q: Docker 容器无法启动？</summary>

A:
1. 检查 `.env` 文件是否存在于项目根目录
2. 确认 Docker 守护进程正在运行：`docker ps`
3. 查看容器日志：`docker-compose logs -f`
4. 确认端口没有被占用
</details>

<details>
<summary>Q: 如何使用其他翻译模型？</summary>

A: 修改 `.env` 文件中的以下配置：
```bash
OPENAI_MODEL=your-model-name
OPENAI_BASE_URL=your-api-endpoint
```
支持任何兼容 OpenAI API 格式的服务。
</details>

<details>
<summary>Q: 如何批量翻译多个 PDF？</summary>

A:
1. Web 界面：支持多文件上传
2. API：循环调用翻译接口
3. 命令行：编写脚本批量处理
4. 注意控制并发数，避免超过 QPS 限制
</details>

<details>
<summary>Q: 翻译后的 PDF 格式错乱？</summary>

A:
1. 确认原 PDF 文件格式标准
2. 尝试使用其他输出模式（双语/单语）
3. 检查日志中是否有格式警告
4. 某些复杂格式可能无法完美保留
</details>

<details>
<summary>Q: 如何提高翻译速度？</summary>

A:
1. 增加 QPS 值（注意 API 限制）
2. 使用更快的模型（如 DeepSeek-V3）
3. 减少输出文件数量（禁用双语输出）
4. 使用更强大的服务器配置
</details>

<details>
<summary>Q: uv 包管理器安装失败？</summary>

A:
1. 使用官方安装脚本：`curl -LsSf https://astral.sh/uv/install.sh | sh`
2. 或使用 pip 安装：`pip install uv`
3. 检查系统兼容性（Linux/macOS/Windows）
4. 如果仍有问题，可以使用传统 pip 方式
</details>

---

## 技术交流群

欢迎加入技术交流群，分享你的使用心得和反馈建议：

![技术交流群](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Screenshot_20260831_150558_com.tencent.mm.jpg)

---

## 作者联系

- **微信**: laohaibao2025
- **邮箱**: 75271002@qq.com

![微信二维码](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Screenshot_20260123_095617_com.tencent.mm.jpg)

---

## 打赏

如果这个项目对你有帮助，欢迎请我喝杯咖啡 ☕

**微信支付**

![微信支付](https://mypicture-1258720957.cos.ap-nanjing.myqcloud.com/Obsidian/image-20250914152855543.png)

---

## Star History

如果觉得项目不错，欢迎点个 Star ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=wwwzhouhui/pdftranslate_web&type=Date)](https://star-history.com/#wwwzhouhui/pdftranslate_web&Date)

---

## License

本项目采用 AGPL-3.0 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 更新日志

### v0.0.1
- 重新整理项目目录结构
- 完善文档和配置文件
- 添加多种部署方式支持
- 优化 API 接口设计
- 集成 uv 包管理器支持

---

## 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

**Enjoy translating your PDF documents with AI! 🚀✨**
