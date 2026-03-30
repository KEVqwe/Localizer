# Localizer 运行指令手册

> 所有命令均在项目根目录 `c:\Users\TU\Desktop\AI应用产品\Localizer` 下执行

---

## 🚀 快速启动（开发模式）

### 1. 激活 Conda 环境

```bash
conda activate py311
```

### 2. 启动 Redis（Docker）

```bash
docker-compose up -d
```

### 3. 启动 FastAPI 后端

```bash
python -m server.src.main
```

后端地址：`http://localhost:8000`

### 4. 启动 Celery Worker（另开终端）

```bash
conda activate py311
celery -A worker.src.celery_tasks worker --loglevel=info -P solo
```

### 5. 启动前端（再开一个终端）

```bash
cd client
npm run dev
```

前端地址：`http://localhost:5173`
---

## 📺 后台离线运行 (推荐)

如果你不希望桌面被 4 个终端窗口占满，可以使用 PM2 将其作为后台服务运行。这样即使你关闭了终端，同事仍然可以使用。

### 1. 启动所有服务
双击根目录下的 `start_services.bat` 即可一键启动后台。

或者手动执行：
```bash
pm2 start ecosystem.config.cjs
```

### 2. 查看状态
```bash
pm2 status
```
你需要看到 `localizer-redis`, `localizer-backend`, `localizer-worker`, `localizer-frontend` 全部为 `online` 绿色状态。

### 3. 查看实时日志 (报错排查)
```bash
pm2 logs
```

### 4. 停止所有服务
```bash
pm2 stop all
```

---

## 🏢 局域网部署（让同事也能用）

### 方法一：开发模式共享（最快）

上面 3 个服务全部启动后，同事直接访问你的内网 IP 即可：

### 1. 查看你的内网 IP：

```powershell
ipconfig
# 找到 "IPv4 地址"，例如 172.16.25.111
```

### 2. 发给同事访问地址：`http://172.16.25.111:8000`

### 3. 防火墙放行（管理员 PowerShell 执行一次即可）：

```powershell
netsh advfirewall firewall add rule name="Localizer API" dir=in action=allow protocol=TCP localport=8000
```

> **注意**：生产模式下前端已打包到后端，只需要 8000 端口，不再需要 5173。

### 方法二：生产模式（只需 1 个端口）

打包前端，让 FastAPI 同时托管 API 和页面，只需要 `8000` 端口：

```bash
# 1. 打包前端
cd client
npm run build

# 2. 回到根目录，启动后端（会自动托管 client/dist）
cd ..
python -m server.src.main
```

同事访问：`http://172.16.25.111:8000`

> 生产模式只需要放行 8000 端口，不需要 5173。

---

## 📥 用户使用流程

1. 打开浏览器 → 输入地址
2. 上传英文视频 → 等待 AI 识别字幕（1-3 分钟）
3. 审核字幕 → 如有落版/Logo 画面，点「标记保护」
4. 点「确认并开始生成」→ 等待翻译配音（3-8 分钟）
5. 在下载页面下载 9 种语言的视频

---

## 🛑 停止服务

```bash
# 停止 Redis
docker-compose down

# 停止 FastAPI 和 Worker：在对应终端按 Ctrl+C
```

---

## ⚙️ 配置项（.env 文件）

| 配置项 | 说明 | 默认值 |
|-------|------|--------|
| `ELEVENLABS_STABILITY` | TTS 稳定性 (0-1) | 0.55 |
| `ELEVENLABS_SIMILARITY` | 声音相似度 (0-1) | 0.9 |
| `ELEVENLABS_STYLE` | 语调风格 (0-1) | 0.15 |
| `INPAINT_TEMPORAL_WEIGHT` | 擦除时序混合权重 | 0.65 |
