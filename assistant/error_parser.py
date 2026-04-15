import re


def simplify_vector_error(exc_or_message) -> str:
    """将向量化异常归一化为用户可读短语。"""
    raw = str(exc_or_message or "").strip()
    if not raw:
        return "向量化失败"
    lower = raw.lower()

    if "authenticationerror" in lower or "incorrect api key" in lower:
        return "OPENAI_API_KEY 缺失或无效"
    if "openai_api_key" in lower or "api_key client option" in lower:
        return "OPENAI_API_KEY 缺失"
    if "moduleNotFoundError".lower() in lower and "langchain" in lower:
        return "未安装 LangChain 依赖"
    if "no module named" in lower and "langchain" in lower:
        return "未安装 LangChain 依赖"
    if "no module named" in lower and "langchain_openai" in lower:
        return "未安装 langchain-openai 依赖"
    if "no module named" in lower and "langchain_chroma" in lower:
        return "未安装 langchain-chroma 依赖"
    if "no module named" in lower and "unstructured" in lower:
        return "未安装 unstructured 依赖"
    if "connection refused" in lower or ("ollama" in lower and "connect" in lower):
        return "Ollama 服务不可达"
    if "timed out" in lower or "timeout" in lower:
        return "向量化服务连接超时"
    if "file not found" in lower or "上传文件不存在" in lower:
        return "源文件不存在或已被移除"
    if "文档内容为空" in raw or "切片后没有有效文本块" in raw:
        return "文档内容为空，无法向量化"

    traceback_hit = re.search(
        r"Traceback \(most recent call last\):", raw, re.IGNORECASE
    )
    if traceback_hit:
        return "向量化失败（内部异常）"
    return raw[:180]
