from app.config import settings

print("LLM_BASE_URL:", settings.llm_base_url)
print("LLM_MODEL:", settings.llm_model)
print("LLM_API_KEY 是否存在:", bool(settings.llm_api_key))