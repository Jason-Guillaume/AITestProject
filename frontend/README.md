# 全流程 AI 测试平台前端

基于 Vue 3 + Vite + Element Plus + Tailwind CSS 的前端工程，用于对接 Django DRF 后端。

## 1. 环境要求

- Node.js 18+
- npm 9+

## 2. 安装与启动

```bash
npm install
npm run dev
```

默认开发地址：`http://localhost:5173`

## 3. 后端联调说明

`vite.config.js` 已配置代理：

- `/api` -> `http://127.0.0.1:8000`

所以前端请求直接写 `/api/...` 即可，不需要手动写完整域名。

## 4. 登录与 Token

- 登录页：`/login`，组件 `src/views/Login.vue`
- 调用后端：`POST /api/user/login/`，请求体 `{ "username": "", "password": "" }`
- 成功后将返回的 `data.token` 写入 `localStorage.token`，再进入业务页

路由守卫（`src/router/index.js`）：未登录访问非公开页会重定向到 `/login`，避免先打接口再 401。

项目在 `src/utils/request.js` 中统一处理业务请求：

- 自动注入：`Authorization: Token <token>`
- 遇到 `401` 会清 token 并跳转 `/login`

本地调试也可手动写入 token（跳过登录页）：

```js
localStorage.setItem("token", "你的DRFToken")
```

## 5. 当前页面与路由

- 登录：`src/views/Login.vue` → `/login`
- 任务管理：`src/views/performance/TaskManagement.vue` → `/performance/tasks`
- 根路径 `/` 会重定向到 `/dashboard`（未登录会先被拦到 `/login`）

## 6. 已对接接口清单

- `GET /api/perf/tasks/` 列表查询（支持分页与筛选）
- `POST /api/perf/tasks/` 新建任务
- `DELETE /api/perf/tasks/{task_id}/` 删除任务
- `POST /api/perf/tasks/{task_id}/run/` 触发执行

## 7. 常见问题排查

- **401 Unauthorized**
  - 检查是否已设置 `localStorage.token`
  - 检查 Django 是否启用 `TokenAuthentication`
  - 检查请求头是否为 `Authorization: Token xxx`

- **接口 404**
  - 检查 Django 是否已挂载：`/api/perf/`
  - 检查后端迁移是否执行：`python manage.py migrate`
  - 检查接口路径是否带尾斜杠（DRF 默认需要）

- **跨域问题**
  - 开发环境优先通过 Vite 代理转发，不要直接跨域请求 Django 域名
  - 若必须直连后端，请在 Django 配置 CORS

- **列表无数据**
  - 先在后端创建几条 `PerfTask`
  - 检查筛选条件是否将数据过滤掉
  - 检查分页参数 `page/page_size`

## 8. 构建发布

```bash
npm run build
npm run preview
```

构建产物目录：`dist/`
