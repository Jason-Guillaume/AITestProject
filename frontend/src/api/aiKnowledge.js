import request from "@/utils/request";

/** POST /api/ai/knowledge/ask/ */
export const askKnowledgeApi = (data) => request.post("/ai/knowledge/ask/", data);

