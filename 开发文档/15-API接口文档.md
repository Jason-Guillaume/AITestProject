# 全流程 AI 测试平台后端 API 文档（性能任务）

本文档用于说明 Django DRF 中性能任务（`PerfTask`）相关接口，供前后端联调与测试使用。

## 1. 基础信息

- 基础前缀：`/api/perf/`
- 鉴权方式：`TokenAuthentication`
- 请求头：

```http
Authorization: Token <your_token>
Content-Type: application/json
```

## 2. 数据模型（PerfTask）

数据库表：`perf_task`

字段说明：

- `task_id`：任务唯一标识（后端自动生成，格式 `PT-0001`）
- `task_name`：任务名称
- `scenario`：测试场景，枚举：`jmeter` / `locust`
- `concurrency`：并发数，范围 `1 ~ 100000`
- `duration`：持续时间，格式 `^\d+[smh]$`（如 `30s`、`10m`、`2h`）
- `status`：任务状态，枚举：`pending` / `running` / `completed` / `failed`
- `executor`：执行人（可为空）
- `create_time` / `update_time`：系统字段
- `created_at`：序列化输出字段，映射自 `create_time`（格式化为 `YYYY-MM-DD HH:mm:ss`）

## 3. 状态流转规则

`POST /run/` 触发执行时：

- `pending` -> `running`（允许）
- `failed` -> `running`（允许）
- `running` -> 400（禁止重复触发）
- `completed` -> 400（禁止直接重跑，建议复制任务）

## 4. 接口清单

### 4.1 获取任务列表（分页 + 筛选）

- 方法：`GET`
- 路径：`/api/perf/tasks/`
- 查询参数：
  - `page`：页码（默认 1）
  - `page_size`：每页条数（默认 10，最大 100）
  - `name`：按任务名称模糊匹配
  - `status`：按状态精确匹配
  - `executor`：按执行人模糊匹配

示例请求：

```http
GET /api/perf/tasks/?page=1&page_size=5&name=登录&status=running&executor=张
```

示例响应：

```json
{
  "count": 12,
  "next": "http://127.0.0.1:8000/api/perf/tasks/?page=2&page_size=5",
  "previous": null,
  "results": [
    {
      "id": 8,
      "task_id": "PT-0008",
      "task_name": "登录接口压测",
      "scenario": "jmeter",
      "concurrency": 200,
      "duration": "15m",
      "status": "running",
      "executor": "张三",
      "created_at": "2026-04-01 20:10:00",
      "create_time": "2026-04-01T12:10:00.000000Z",
      "update_time": "2026-04-01T12:10:00.000000Z",
      "is_deleted": false,
      "creator": 1,
      "updater": 1
    }
  ]
}
```

### 4.2 新建任务

- 方法：`POST`
- 路径：`/api/perf/tasks/`

请求体示例：

```json
{
  "task_name": "订单峰值压测",
  "scenario": "locust",
  "concurrency": 500,
  "duration": "30m",
  "status": "pending",
  "executor": "李四"
}
```

成功响应（201）示例：

```json
{
  "id": 9,
  "task_id": "PT-0009",
  "task_name": "订单峰值压测",
  "scenario": "locust",
  "concurrency": 500,
  "duration": "30m",
  "status": "pending",
  "executor": "李四",
  "created_at": "2026-04-01 20:12:20"
}
```

校验失败示例（400）：

```json
{
  "duration": ["持续时间格式错误，应为如 30s、10m、2h"]
}
```

### 4.3 删除任务

- 方法：`DELETE`
- 路径：`/api/perf/tasks/{task_id}/`
- 说明：软删除（`is_deleted = true`）

示例请求：

```http
DELETE /api/perf/tasks/PT-0009/
```

成功响应：`204 No Content`

### 4.4 触发执行

- 方法：`POST`
- 路径：`/api/perf/tasks/{task_id}/run/`

示例请求：

```http
POST /api/perf/tasks/PT-0008/run/
```

成功响应（200）示例：

```json
{
  "detail": "任务已触发执行",
  "task_id": "PT-0008"
}
```

失败响应（400）示例：

```json
{
  "detail": "任务正在运行中，无需重复触发"
}
```

## 5. 本地初始化步骤

在后端根目录执行：

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_perf_tasks
python manage.py runserver
```

- 若出现 **`Table '...perf_task' doesn't exist`**，说明未执行迁移，请先运行 `python manage.py migrate`。
- `seed_perf_tasks` 仅在当前没有任何未删除的性能任务时插入 6 条演示数据；已有数据则跳过。
- 注册接口用到的图片验证码依赖包 **`captcha`**；若未安装，仅影响 `/api/user/captcha/`，不影响登录与性能任务接口。

## 6. 备注

- 本接口使用 `lookup_field = "task_id"`，路径参数应传 `PT-xxxx`，不是数据库主键 `id`。
- DRF 默认带尾斜杠，建议前端统一保留 `/`，避免 301/404 问题。
