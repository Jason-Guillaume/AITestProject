# OCR 验证码处理流程模块（Tool‑01）

## I. 业务深度逻辑 (Business Logic Deep Dive)
1. **验证码生成与校验**
   - 前端在登录、敏感操作等场景调用 `GET /api/captcha/`（`CaptchaAPIView`），后端使用 `CleanTechCaptcha`（`user/captcha_image.py`）随机生成 4~6 位字符并绘制噪点、干扰线的 PNG 图片。
   - 生成的字符 **存入用户 Session**（`request.session['captcha']`），并将图片二进制写入 `HttpResponse(content_type='image/png')` 返回给前端。
   - 前端展示图片后，用户输入验证码，提交至对应业务 API（如 `POST /api/user/login/`）时，后端通过 `request.session.get('captcha')` 与用户提交的 `captcha` 字段进行 **大小写不敏感** 对比，匹配成功后继续业务流程，否则返回 `400` 错误。
2. **第三方 OCR 识别（dddocr）**
   - 为了提升可访问性或在移动端自动化测试中免除手工输入，可选调用 **`ddddocr`**（已在 `requirements.txt` 中声明）将验证码图片进行 OCR 识别。
   - 项目在 `assistant/services/ocr_service.py` 中提供封装函数：
     ```python
     from ddddocr import DdddOcr
     import base64

     def ocr_identify(image_bytes: bytes) -> str:
         ocr = DdddOcr(show_ad=False)
         result = ocr.classification(image_bytes)
         return result.strip()
     ```
   - 该函数在 **后台自动化脚本**（如 UI 自动化或压力测试）中被调用：先获取验证码图片的 **Base64**，再通过 `ocr_identify` 获取文字，随后填入登录请求的 `captcha` 字段，实现全链路自动化。
3. **安全防护与限制**
   - 验证码生成频率受 `settings.CAPTCHA_RATE_LIMIT`（每分钟最多 30 次）控制，超过阈值返回 `429 Too Many Requests`。
   - 生成的字符在 **Session** 中保存时使用 `hashlib.sha256` 加盐后存储，防止会话泄漏后被直接读取。
   - OCR 接口仅在 **内部服务**（`X-Internal-Request` Header）或 **管理员 token** 授权下可用，防止外部滥用导致验证码失效。

## II. 数据库全解析 (Database Schema & Visibility)

| 表 | 字段 | 类型 | 空/默认 | 可见性 |
|---|------|------|----------|--------|
| `user_captcha` *(虚拟表，仅用于说明)* | `session_key` | VARCHAR(40) | 否 | 后端私有 |
| | `code_hash` | VARCHAR(64) | 否 | 后端私有 |
| | `created_at` | DATETIME | 自动 | 后端私有 |

> **说明**：验证码不持久化到数据库，而是保存在 **Session**（或 Redis 缓存）中，此表仅用于概念说明。

## III. 交互生命周期 (Interaction Lifecycle)

| 前端动作 | API | 请求示例 | 后端处理 | 响应 |
|----------|-----|----------|----------|------|
| 请求验证码图片 | `GET /api/captcha/` | — | `CleanTechCaptcha.generate_image` → 保存字符至 `session['captcha']` → 返回 PNG 图片 | `image/png` 二进制流 |
| 手动提交验证码 | `POST /api/user/login/` (登录示例) | `{ "username":"admin","password":"pwd","captcha":"AB12" }` | 从 `session` 读取字符并比较，若匹配继续登录，否则返回错误 | `{ "code":1, "msg":"验证码错误" }` |
| 自动化脚本获取验证码并 OCR | 调用内部 `POST /api/internal/ocr/` | `{ "image_base64":"..." }` (内部) | `ocr_identify` 解析图片 → 返回文字 | `{ "text":"AB12" }` |

## IV. 前端呈现与 UI 规范 (Frontend & UI Spec)
- **验证码展示**：使用 `<img :src="`data:image/png;base64,${captchaBase64}`" alt="验证码" />`，每次刷新按钮调用 `api/getCaptcha()` 更新 `captchaBase64`。
- **刷新按钮**：`a-button` 采用 **Cyberpunk Blue** 样式，点击时发送 `GET /api/captcha/` 并更新图片。
- **错误提示**：验证码错误返回 `code=1`，前端统一在 `LoginForm` 中以红色提示 `验证码错误，请重新输入`。
- **可访问性**：为视障用户提供 **音频验证码**（可选）接口 `GET /api/captcha/audio/`，返回 `audio/mpeg`，实现文字转语音（使用 `gTTS`）。
- **主题统一**：验证码区域背景 `#0a0f1f`，输入框边框 `1px solid #1f8ef1`，错误文字颜色 `#ff4d4f`。

## V. 模块拆分颗粒度 (Module Granularity)

| 子模块 | 说明 |
|--------|------|
| **Captcha Generator** (`user.captcha_image.CleanTechCaptcha`) | 负责随机字符生成、图像绘制、噪点添加。
| **Captcha View** (`user.views.CaptchaAPIView`) | 提供图片、音频两种返回形式，写入 Session 并返回二进制流。
| **OCR Service** (`assistant.services.ocr_service`) | 基于 `ddddocr` 的封装函数 `ocr_identify`，供内部脚本调用。
| **RateLimiter Middleware** (`common/middleware.py` 示例) | 限制 `/api/captcha/` 调用频率，防止暴力攻击。
| **Frontend Component** (`frontend/src/components/Captcha.vue`) | 展示图片、刷新按钮、错误提示，统一 UI 风格。
