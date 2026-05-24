from app.config import settings

print("WEB_SEARCH_PROVIDER:", settings.web_search_provider)
print("TAVILY_API_KEY 是否存在:", bool(settings.tavily_api_key))
print("WEB_SEARCH_MAX_RESULTS:", settings.web_search_max_results)