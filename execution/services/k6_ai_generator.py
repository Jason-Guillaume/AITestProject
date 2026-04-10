"""
调用大模型将 API 业务链路 JSON 转为可执行的 k6 脚本。
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

from testcase.services.ai_openai import chat_completion

from execution.services.k6_chain_builder import chain_to_prompt_json

_SYSTEM = """你是资深性能测试工程师，负责把 API 调用链路转换为 k6 (Grafana k6) 可运行的 JavaScript 脚本。

硬性要求：
1. 只输出一段完整可运行的 k6 脚本，不要 Markdown 说明文字；如需代码围栏仅使用 ```javascript。
2. 必须使用：import http from 'k6/http'; import { check, sleep } from 'k6';
3. 必须 export const options = { vus: <int>, duration: '<k6 duration>' }; 其中 vus、duration 使用用户在提示中给出的值。
4. 必须 export default function () { ... }，在函数内按顺序发起 HTTP 请求，步骤之间 sleep(0.1~0.5)。
5. 使用链表中给出的完整 URL；请求方法、请求头、JSON 请求体必须与链路一致。
6. 对每一步用 check() 校验状态码：若提供 expected_status 则等于该值，否则校验 2xx。
7. 不要引用 Node.js 模块；不要使用未在 k6 标准库中的 import。
"""


def extract_js_from_model_output(text: str) -> str:
    t = (text or "").strip()
    m = re.search(r"```(?:javascript|js)?\s*([\s\S]*?)```", t, re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return t


def generate_k6_script_with_ai(
    steps: list,
    vus: int,
    duration: str,
    *,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    chain_json = chain_to_prompt_json(steps)
    user = f"""请根据以下 API 链路生成 k6 脚本。

运行参数：vus = {vus}, duration = {duration!r}

链路 JSON：
{chain_json}
"""
    raw, err = chat_completion(
        _SYSTEM,
        user,
        api_key=api_key,
        base_url=base_url,
        model=model,
        max_tokens=4096,
        temperature=0.1,
    )
    if err or not raw:
        return None, err or "模型无输出"
    js = extract_js_from_model_output(raw)
    if "export default function" not in js:
        return None, "模型输出缺少 export default function"
    if "import http from 'k6/http'" not in js:
        return None, "模型输出缺少 k6/http import"
    return js, None
