import axios from "axios";

/**
 * 登录使用独立 axios，避免与业务 request 拦截器耦合。
 * 后端：POST /api/user/login/  body: { username, password }
 */
export function loginApi(payload) {
  return axios.post("/api/user/login/", payload, {
    headers: { "Content-Type": "application/json" },
  });
}

/**
 * 获取图片验证码
 * GET /api/user/captcha/
 * 返回：
 * { code: 200, msg: "...", data: { uuid, image } }
 */
export function captchaApi() {
  return axios.get("/api/user/captcha/");
}

/**
 * 注册
 * POST /api/user/register/
 * body: { username, password, captcha_code, captcha_uuid }
 */
export function registerApi(payload) {
  return axios.post("/api/user/register/", payload, {
    headers: { "Content-Type": "application/json" },
  });
}
