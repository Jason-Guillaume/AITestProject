# Test Connection - Quick Reference

## 🚀 Quick Start (3 Steps)

### 1. Start Dev Server
```bash
cd frontend
npm run dev
```

### 2. Navigate to Config Page
- Open: `http://localhost:5173`
- Go to: **智能助手 → 模型接入**

### 3. Test Your API
```
Base URL:    (leave blank for api.iamhc.cn)
API Key:     your-api-key-here
Model ID:    gpt-4o
```
Click **"测试连接"** ✅

---

## 📋 Common Test Scenarios

### Scenario 1: Test with api.iamhc.cn (Uses Proxy)
```
Base URL:    [blank]
API Key:     sk-xxx
Model ID:    gpt-4o
```
✅ Proxy automatically handles CORS

### Scenario 2: Test with OpenAI
```
Base URL:    https://api.openai.com/v1
API Key:     sk-proj-xxx
Model ID:    gpt-4o
```
✅ Direct connection (no proxy)

### Scenario 3: Test with Custom Provider
```
Base URL:    https://your-api.com/v1
API Key:     your-key
Model ID:    your-model-name
```
✅ Works with any OpenAI-compatible API

---

## 🎯 What Happens When You Click "测试连接"

1. **Validation** - Checks API Key and Model ID are filled
2. **Loading State** - Button shows "Connecting..." with spinner
3. **API Request** - Sends chat completion request to AI model
4. **Response** - Shows actual AI response or detailed error

---

## ✅ Success Response Shows

- ✅ Green checkmark icon
- ✅ "Connection successful!" message
- ✅ Model name used
- ✅ Actual AI response text
- ✅ Token usage (prompt + completion = total)

**Example:**
```
✓ Connection successful!

Model: gpt-4o
Response: Hello! I'm here and ready to assist you. How can I help you today?
Usage: 15 prompt + 18 completion = 33 tokens
```

---

## ❌ Error Response Shows

- ❌ Red X icon
- ❌ Specific error message
- ❌ Human-readable details
- ❌ Technical info (JSON)

**Common Errors:**

| Error | Meaning | Solution |
|-------|---------|----------|
| 401 Unauthorized | Invalid API Key | Check your API key |
| 404 Not Found | Wrong endpoint | Verify Base URL |
| Network Timeout | No response | Check internet/URL |
| 429 Too Many Requests | Rate limit | Wait and retry |

---

## 🔧 Proxy Configuration

**File:** `frontend/vite.config.js`

```javascript
proxy: {
  "/ai-api": {
    target: "https://api.iamhc.cn",
    changeOrigin: true,
    rewrite: (path) => path.replace(/^\/ai-api/, ""),
    secure: true,
    timeout: 30_000,
  }
}
```

**How it works:**
- Browser → `http://localhost:5173/ai-api/v1/chat/completions`
- Proxy → `https://api.iamhc.cn/v1/chat/completions`
- No CORS issues! ✅

---

## 🐛 Quick Troubleshooting

### Problem: CORS Error
**Fix:** Leave Base URL blank (uses proxy automatically)

### Problem: 401 Unauthorized
**Fix:** Double-check API Key (no spaces)

### Problem: 404 Not Found
**Fix:** Ensure Base URL ends with `/v1`

### Problem: Network Timeout
**Fix:** Check internet connection and Base URL

### Problem: Component not showing
**Fix:** Restart dev server: `npm run dev`

---

## 📝 Request Details

**What gets sent to the AI API:**

```json
POST /v1/chat/completions
Headers:
  Content-Type: application/json
  Authorization: Bearer YOUR_API_KEY

Body:
{
  "model": "gpt-4o",
  "messages": [
    {
      "role": "user",
      "content": "Hello! Please respond with a simple greeting to confirm the connection."
    }
  ],
  "max_tokens": 50,
  "temperature": 0.7
}
```

---

## 🎨 UI States

| State | Button Text | Button Disabled | Spinner |
|-------|-------------|-----------------|---------|
| Idle | 测试连接 | No | No |
| Testing | Connecting... | Yes | Yes |
| Success | 测试连接 | No | No |
| Error | 测试连接 | No | No |

---

## 🔐 Security Notes

- ✅ API Key is password-masked
- ✅ API Key never logged to console
- ✅ 30-second timeout prevents hanging
- ✅ HTTPS enforced for proxy
- ⚠️ Never commit API Keys to git
- ⚠️ Proxy only works in development

---

## 📦 Files Modified

```
frontend/
├── vite.config.js                    # Added /ai-api proxy
└── src/
    └── components/
        └── ModelConfigForm.vue       # Added test logic + UI
```

---

## 🧪 Test Checklist

- [ ] Valid API key → Shows success ✅
- [ ] Invalid API key → Shows 401 error ❌
- [ ] Blank Base URL → Uses proxy
- [ ] Custom Base URL → Direct connection
- [ ] Button shows "Connecting..." during test
- [ ] Success shows AI response
- [ ] Error shows specific message
- [ ] Multiple tests work correctly

---

## 💡 Pro Tips

1. **Leave Base URL blank** for api.iamhc.cn (uses proxy)
2. **Check browser console** for detailed logs
3. **Test with a simple model first** (e.g., gpt-3.5-turbo)
4. **Watch for rate limits** - don't spam the test button
5. **Use Advanced Configuration** for custom headers if needed

---

## 📞 Need Help?

1. Check browser console (F12) for errors
2. Verify dev server is running
3. Confirm axios is installed: `npm list axios`
4. Review full documentation: `TEST_CONNECTION_IMPLEMENTATION.md`

---

**Status:** ✅ Ready to Use

**Quick Test:**
```bash
cd frontend && npm run dev
# Open http://localhost:5173
# Go to: 智能助手 → 模型接入
# Fill in API Key and Model ID
# Click "测试连接"
```
