# 视频导出并发改进设计文档

> 变更类型：设计文档（不改代码）
> 创建时间：2026-04-07 05:06
> 分支：118v3

---

## 1. 现状分析

### 1.1 当前并发模型

视频导出的调用链路：

```
用户请求 POST /api/scenes/{scene_id}/export-video
  → main.py:export_scene_video()  (L2053, 同步 FastAPI handler)
    → video_generator.create_export_job()   (L475, 创建 job 记录)
    → video_generator.start_export()        (L545, 启动后台线程)
      → threading.Thread(target=_run_export, daemon=True)
        → _run_export()                     (L515, 实际 FFmpeg 调用)
```

`start_export()` 每次被调用都直接 `threading.Thread(...).start()`，没有任何并发控制机制。

### 1.2 存在的问题

| 问题 | 说明 | 影响 |
|------|------|------|
| **无并发限制** | 每个导出请求启动一个新线程，直接调用 FFmpeg | N 个用户同时导出 = N 个 FFmpeg 进程并行，CPU 打满 |
| **无速率限制** | API 端点没有 `@limiter.limit` 装饰器 | 单个用户可以高频重复请求，快速耗尽服务器资源 |
| **无去重** | 同一场景同一用户可以反复创建导出任务 | 浪费资源，重复生成相同视频 |
| **无背压** | `_jobs` 是内存 dict，无容量上限 | 如果请求持续堆积，内存可能溢出（虽然单条 job 很小，但理论上无保护） |
| **无队列优先级** | 所有请求平等对待，先到先得 | 高优先级用户与普通用户争抢资源 |

### 1.3 资源消耗估算

单个视频导出的资源消耗：
- **CPU**: FFmpeg `libx264` 编码，单线程约 60-100% CPU
- **内存**: 约 200-500MB（取决于视频长度和分辨率）
- **磁盘 I/O**: 临时文件 + 最终 MP4，约 10-50MB
- **耗时**: 典型 10-40 秒（取决于场景中 item 数量）

假设服务器 4 核：**2 个并行 FFmpeg 已接近饱和**，第 3 个开始严重争抢 CPU。

---

## 2. 改进方案

推荐方案：**Semaphore + Rate Limit + 去重**，最小改动量，无需引入新依赖。

### 2.1 全局并发信号量

在 `video_generator.py` 添加 `threading.Semaphore`，限制同时运行的 FFmpeg 进程数。

```python
# video_generator.py 新增

# 全局并发限制：同时最多 2 个 FFmpeg 进程
_MAX_CONCURRENT_EXPORTS = int(os.getenv('VIDEO_EXPORT_MAX_CONCURRENT', '2'))
_export_semaphore = threading.Semaphore(_MAX_CONCURRENT_EXPORTS)
```

`start_export()` 中在线程函数内部使用信号量：

```python
def _run_export(job_id: str, scene: dict, assets_root: Path) -> None:
    # 等待信号量（阻塞直到有空位）
    acquired = _export_semaphore.acquire(timeout=600)  # 最多等 10 分钟
    if not acquired:
        _update_job(job_id, status='failed', message='导出排队超时，请稍后重试')
        return
    try:
        _update_job(job_id, status='processing', message='开始生成视频...')
        # ... 原有逻辑不变 ...
    except Exception as exc:
        # ... 原有错误处理 ...
    finally:
        _export_semaphore.release()
```

### 2.2 API 速率限制

在 `main.py` 的导出端点添加速率限制装饰器。

项目已有 `slowapi` 的 `limiter` 实例（用于其他端点），直接复用：

```python
# main.py L2053 添加装饰器
@app.post('/api/scenes/{scene_id}/export-video')
@limiter.limit("3/minute")   # 每用户每分钟最多 3 次导出请求
def export_scene_video(scene_id: str, request: Request):
    # ... 原有逻辑不变 ...
```

> **注意**: 如果 `limiter` 未在 `main.py` 中初始化，需要先确认 `slowapi` 已安装并正确配置。
> 检查 `requirements.txt` 和 `main.py` 中的 `Limiter` 导入。

### 2.3 同场景去重

在 `export_scene_video()` 中检查是否已有该场景的活跃导出任务：

```python
# video_generator.py 新增

def has_active_export(scene_id: str, user_id: str) -> Optional[str]:
    """检查同一用户对同一场景是否有进行中的导出，返回已有 job_id 或 None。"""
    with _jobs_lock:
        for job_id, job in _jobs.items():
            if (job.get('sceneId') == scene_id
                    and job.get('userId') == user_id
                    and job.get('status') in ('pending', 'processing')):
                return job_id
    return None
```

```python
# main.py export_scene_video() 中，创建 job 之前添加：

existing_job = has_active_export(scene_id, user.get('id', ''))
if existing_job:
    return success({
        'jobId': existing_job,
        'status': 'processing',
        'message': '该场景正在导出中，请等待完成'
    })
```

---

## 3. 代码改动点

### 3.1 `backend/app/video_generator.py`

| 行号 | 改动 | 说明 |
|------|------|------|
| L20 (import 后) | 新增 `_export_semaphore` | `threading.Semaphore` 全局实例 |
| L515 `_run_export()` | 函数体内包裹信号量 `acquire/release` | 控制并发 |
| 新增函数 | `has_active_export()` | 同场景去重检查 |
| 新增环境变量 | `VIDEO_EXPORT_MAX_CONCURRENT` | 可配置并发上限，默认 2 |

### 3.2 `backend/app/main.py`

| 行号 | 改动 | 说明 |
|------|------|------|
| L2053 | 添加 `@limiter.limit("3/minute")` 装饰器 | 速率限制 |
| L2077 (create 之前) | 调用 `has_active_export()` 去重 | 防止重复导出 |

### 3.3 `backend/.env.example`

新增配置项：

```env
# Video export concurrency limit
VIDEO_EXPORT_MAX_CONCURRENT=2
```

### 3.4 无需改动的文件

- `backend/app/access_control.py` — 权限检查逻辑不变
- `backend/app/settings.py` — 配置项通过 `os.getenv()` 直接读取，可选加入 Settings 类

---

## 4. 方案对比（备选）

| 方案 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **A: Semaphore + Rate Limit + 去重** | 最小改动，无新依赖，够用 | 不支持持久化队列，重启丢失排队信息 | 推荐 |
| B: Celery + Redis 队列 | 企业级方案，支持持久化、重试、监控 | 引入新依赖，架构复杂度高 | 量大时考虑 |
| C: `asyncio.Semaphore` + 进程池 | 与 FastAPI async 天然契合 | 当前 `video_generator` 是同步代码，改造成本大 | 长期可选 |

---

## 5. 验证方法

### 5.1 并发控制验证

```bash
# 同时发送 4 个导出请求
for i in $(seq 1 4); do
  curl -X POST "https://e.cps.vin/api/scenes/{scene_id}/export-video" \
    -H "Authorization: Bearer {token}" &
done
wait

# 观察日志：应只有 2 个 FFmpeg 进程同时运行
# 其他 2 个应处于 pending 状态，等待信号量
ps aux | grep ffmpeg | wc -l   # 应 <= 2
```

### 5.2 速率限制验证

```bash
# 快速发送 4 次请求
for i in $(seq 1 4); do
  curl -s -o /dev/null -w "%{http_code}" \
    -X POST "https://e.cps.vin/api/scenes/{scene_id}/export-video" \
    -H "Authorization: Bearer {token}"
  echo ""
done
# 第 4 次应返回 429 Too Many Requests
```

### 5.3 去重验证

```bash
# 对同一场景连续发送 2 次请求
JOB1=$(curl -s -X POST "https://e.cps.vin/api/scenes/{scene_id}/export-video" \
  -H "Authorization: Bearer {token}" | jq -r '.data.jobId')

JOB2=$(curl -s -X POST "https://e.cps.vin/api/scenes/{scene_id}/export-video" \
  -H "Authorization: Bearer {token}" | jq -r '.data.jobId')

# 第二次应返回第一次的 jobId（或提示"正在导出中"）
echo "JOB1=$JOB1 JOB2=$JOB2"
# 预期: JOB1 == JOB2
```

### 5.4 压力测试

使用 `ab` 或 `wrk` 模拟 10 个并发用户同时触发导出，确认：
- CPU 使用率不超过 80%
- 内存无异常增长
- 所有 job 最终都能完成（不丢失）
- 响应时间在可接受范围内

---

## 6. 相关文件索引

| 文件 | 关键位置 | 说明 |
|------|----------|------|
| `backend/app/video_generator.py` | L464 `_jobs` | 任务存储 dict |
| `backend/app/video_generator.py` | L515 `_run_export()` | 后台导出执行函数 |
| `backend/app/video_generator.py` | L545 `start_export()` | 启动导出线程 |
| `backend/app/main.py` | L2053 `export_scene_video()` | API 端点 handler |
| `backend/app/access_control.py` | L107 `check_video_export_permission()` | 权限检查 |
| `backend/app/settings.py` | 环境变量读取 | 配置管理 |
