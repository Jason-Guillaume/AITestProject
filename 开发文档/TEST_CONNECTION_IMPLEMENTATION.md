# Test Connection Implementation - Complete Guide

## ✅ What Was Implemented

### 1. Vite Proxy Configuration
**File:** `frontend/vite.config.js`

Added a new proxy route to bypass CORS when testing AI model connections:

```javascript
"/ai-api": {
  target: "https://api.iamhc.cn",
  changeOrigin: true,
  rewrite: (path) => path.replace(/^\/ai-api/, ""),
  secure: true,
  timeout: 30_000,
}
```

**How it works:**
- Browser requests: `http://localhost:5173/ai-api/v1/chat/completions`
- Vite proxy forwards to: `https://api.iamhc.cn/v1/chat/completions`
- Response comes back through the proxy (no CORS issues)

### 2. Real Backend Connectivity Logic
**File:** `frontend/src/components/ModelConfigForm.vue`

#### Key Features Implemented:

**A. State Management**
```javascript
const isTesting = ref(false)        // Loading state
const testResult = ref(null)        // Success response
const testError = ref(null)         // Error details
```

**B. Connection Test Function**
The `handleTest()` function now:
1. ✅ Validates API Key and Model ID
2. ✅ Determines the correct endpoint URL
3. ✅ Uses proxy for CORS bypass (when using api.iamhc.cn)
4. ✅ Injects Authorization header with Bearer token
5. ✅ Sends a real chat completion request
6. ✅ Displays actual AI response
7. ✅ Shows detailed error messages with status codes

**C. Request Payload**
```javascript
{
  model: formData.modelId.trim(),
  messages: [
    {
      role: 'user',
      content: 'Hello! Please respond with a simple greeting to confirm the connection.'
    }
  ],
  max_tokens: 50,
  temperature: 0.7
}
```

**D. Error Handling**
Specific error messages for:
- ✅ 401 Unauthorized - Invalid API Key
- ✅ 403 Forbidden - Access denied
- ✅ 404 Not Found - Invalid endpoint
- ✅ 429 Too Many Requests - Rate limit
- ✅ 500 Internal Server Error
- ✅ Network Timeout - No response
- ✅ Request Error - Failed to send

### 3. UI Enhancements

**A. Button States**
- Default: "测试连接"
- Loading: "Connecting..." with spinner
- Disabled during save/test operations

**B. Success Display**
Shows:
- ✅ Success icon (green checkmark)
- ✅ Model name used
- ✅ Actual AI response text
- ✅ Token usage statistics

**C. Error Display**
Shows:
- ✅ Error icon (red X)
- ✅ Error message (e.g., "401 Unauthorized")
- ✅ Human-readable details
- ✅ Technical info (JSON response)

## 🔧 How to Use

### Step 1: Start Development Server
```bash
cd frontend
npm run dev
```

The proxy will automatically be active at `http://localhost:5173`

### Step 2: Navigate to Configuration
1. Open browser: `http://localhost:5173`
2. Login to AITesta
3. Go to: **智能助手 → 模型接入** tab

### Step 3: Test Connection

#### Example 1: Using Default Proxy (api.iamhc.cn)
```
Base URL:    (leave blank or enter https://api.iamhc.cn/v1)
API Key:     your-api-key-here
Model ID:    gpt-4o
```
Click **"测试连接"** → Uses proxy automatically

#### Example 2: Using Custom Endpoint
```
Base URL:    https://api.openai.com/v1
API Key:     sk-proj-abc123...
Model ID:    gpt-4o
```
Click **"测试连接"** → Direct connection (no proxy)

#### Example 3: With Custom Headers
1. Expand **"Advanced Configuration"**
2. Add custom headers:
   - Key: `X-Custom-Auth`, Value: `Bearer token123`
   - Key: `X-Request-ID`, Value: `req-456`
3. Click **"测试连接"**

## 📊 Response Examples

### Success Response
```json
{
  "success": true,
  "message": "Connection successful!",
  "response": "Hello! I'm here and ready to assist you. How can I help you today?",
  "model": "gpt-4o",
  "usage": {
    "prompt_tokens": 15,
    "completion_tokens": 18,
    "total_tokens": 33
  }
}
```

### Error Response (401)
```json
{
  "success": false,
  "message": "401 Unauthorized",
  "details": "Invalid API Key. Please check your credentials.",
  "fullError": {
    "error": {
      "message": "Incorrect API key provided",
      "type": "invalid_request_error",
      "code": "invalid_api_key"
    }
  }
}
```

### Error Response (Network Timeout)
```json
{
  "success": false,
  "message": "Network Timeout",
  "details": "No response from server. Check your Base URL and network connection.",
  "fullError": "timeout of 30000ms exceeded"
}
```

## 🔍 Technical Details

### Proxy Logic
```javascript
// Determine if we should use the proxy
const useProxy = apiUrl.includes('api.iamhc.cn')

// Choose the correct URL
const requestUrl = useProxy
  ? '/ai-api/v1/chat/completions'  // Proxy route
  : `${apiUrl}/chat/completions`    // Direct connection
```

### Headers Construction
```javascript
const headers = {
  'Content-Type': 'application/json',
  'Authorization': `Bearer ${formData.apiKey.trim()}`
}

// Add custom headers
formData.customHeaders.forEach(header => {
  if (header.key && header.value) {
    headers[header.key] = header.value
  }
})
```

### Axios Configuration
```javascript
const response = await axios.post(requestUrl, payload, {
  headers,
  timeout: 30000  // 30 second timeout
})
```

## 🐛 Troubleshooting

### Issue 1: CORS Error
**Symptom:** Browser console shows "CORS policy" error

**Solution:**
1. Make sure dev server is running (`npm run dev`)
2. Verify proxy is configured in `vite.config.js`
3. For api.iamhc.cn, leave Base URL blank (uses proxy automatically)
4. Restart dev server after changing vite.config.js

### Issue 2: 401 Unauthorized
**Symptom:** Error message "Invalid API Key"

**Solution:**
1. Double-check your API Key (no extra spaces)
2. Verify the key is valid for the model you're testing
3. Check if the key has proper permissions

### Issue 3: 404 Not Found
**Symptom:** Error message "API endpoint not found"

**Solution:**
1. Verify Base URL format (should end with `/v1`)
2. Check if the endpoint supports `/chat/completions`
3. Try with default proxy first (leave Base URL blank)

### Issue 4: Network Timeout
**Symptom:** "No response from server" after 30 seconds

**Solution:**
1. Check your internet connection
2. Verify the Base URL is correct
3. Try a different model (some models are slower)
4. Check if the API service is online

### Issue 5: Component Not Rendering
**Symptom:** Blank page or console errors

**Solution:**
1. Check browser console for errors
2. Verify axios is installed: `npm list axios`
3. Clear browser cache and reload
4. Restart dev server

## 🔐 Security Considerations

### ✅ Implemented
- API Key is never logged to console
- Password field with visibility toggle
- API Key cleared after successful save
- 30-second timeout prevents hanging requests
- HTTPS enforced for proxy target

### ⚠️ Important Notes
1. **Never commit API Keys** to version control
2. **Use environment variables** for production API keys
3. **Proxy is for development only** - production should use backend API
4. **Rate limiting** - Be mindful of API usage limits

## 🚀 Production Deployment

### Important: Proxy Won't Work in Production

The Vite proxy only works in development. For production:

**Option 1: Use Backend Proxy (Recommended)**
```javascript
// Instead of direct API calls, use your backend
const response = await axios.post('/api/ai/test-connection', {
  api_key: formData.apiKey,
  model: formData.modelId,
  base_url: formData.baseUrl
})
```

**Option 2: CORS-Enabled API**
Ensure your AI API provider has CORS enabled for your domain.

**Option 3: Server-Side Proxy**
Set up nginx or similar to proxy AI API requests.

### Build for Production
```bash
cd frontend
npm run build
```

The proxy configuration in `vite.config.js` will be ignored in the build.

## 📝 Code Flow Diagram

```
User clicks "测试连接"
         ↓
Validate API Key & Model ID
         ↓
Determine endpoint URL
         ↓
Check if proxy needed (api.iamhc.cn)
         ↓
    ┌────┴────┐
    ↓         ↓
Use Proxy   Direct
/ai-api     Connection
    ↓         ↓
    └────┬────┘
         ↓
Construct headers (Authorization + Custom)
         ↓
Send POST request with chat completion payload
         ↓
    ┌────┴────┐
    ↓         ↓
Success    Error
    ↓         ↓
Display    Parse error
response   (401/404/timeout)
    ↓         ↓
Show AI    Show error
message    details
```

## 🧪 Testing Checklist

- [ ] Test with valid API key → Should show success
- [ ] Test with invalid API key → Should show 401 error
- [ ] Test with blank Base URL → Should use proxy
- [ ] Test with custom Base URL → Should use direct connection
- [ ] Test with custom headers → Should include in request
- [ ] Test button shows "Connecting..." during request
- [ ] Test button is disabled during request
- [ ] Success shows AI response text
- [ ] Success shows token usage
- [ ] Error shows specific error message
- [ ] Error shows technical details
- [ ] Network timeout shows appropriate message
- [ ] Multiple tests in a row work correctly
- [ ] Previous results are cleared on new test

## 📚 API Reference

### OpenAI-Compatible Chat Completion Endpoint

**Endpoint:** `POST /v1/chat/completions`

**Headers:**
```
Content-Type: application/json
Authorization: Bearer YOUR_API_KEY
```

**Request Body:**
```json
{
  "model": "gpt-4o",
  "messages": [
    {
      "role": "user",
      "content": "Hello!"
    }
  ],
  "max_tokens": 50,
  "temperature": 0.7
}
```

**Response:**
```json
{
  "id": "chatcmpl-123",
  "object": "chat.completion",
  "created": 1677652288,
  "model": "gpt-4o",
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Hello! How can I help you today?"
      },
      "finish_reason": "stop"
    }
  ],
  "usage": {
    "prompt_tokens": 9,
    "completion_tokens": 12,
    "total_tokens": 21
  }
}
```

## 🎯 Next Steps

### Recommended Enhancements
1. **Add model presets** - Quick select for common models
2. **Add connection history** - Track successful/failed tests
3. **Add response time display** - Show latency
4. **Add streaming support** - Real-time response display
5. **Add batch testing** - Test multiple configurations
6. **Add configuration profiles** - Save/load different setups

### Backend Integration
For production, implement a backend endpoint:

```python
# backend/assistant/views.py
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_ai_connection(request):
    api_key = request.data.get('api_key')
    model = request.data.get('model')
    base_url = request.data.get('base_url', 'https://api.iamhc.cn/v1')
    
    try:
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                'Authorization': f'Bearer {api_key}',
                'Content-Type': 'application/json'
            },
            json={
                'model': model,
                'messages': [{'role': 'user', 'content': 'Hello!'}],
                'max_tokens': 50
            },
            timeout=30
        )
        
        return Response({
            'success': True,
            'data': response.json()
        })
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=400)
```

---

**Status:** ✅ Fully Implemented and Ready for Testing

**Last Updated:** 2026-04-29
