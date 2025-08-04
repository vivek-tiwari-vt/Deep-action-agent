import os
import re
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def clean_api_keys(keys_string: str) -> list:
    """Clean and parse API keys from environment variable, handling multi-line format."""
    if not keys_string:
        return []
    
    # Remove all whitespace and newlines, then split by comma
    cleaned = re.sub(r'\s+', '', keys_string)
    keys = [key.strip() for key in cleaned.split(',') if key.strip()]
    
    # Filter out placeholder keys and empty strings
    keys = [key for key in keys if key not in ['key1', 'key2', ''] and len(key) > 10]
    
    return keys

def get_env_var(var_name: str, default: str = "") -> str:
    """Get environment variable with proper error handling."""
    value = os.getenv(var_name, default)
    if not value:
        print(f"Warning: {var_name} not found in environment variables")
    return value

def get_provider_from_model(model_name: str) -> str:
    """Determine the provider from model name."""
    if not model_name:
        return 'gemini'  # Default fallback
    
    # Gemini models (no prefix or google/ prefix)
    if model_name.startswith('gemini-') or model_name.startswith('google/gemini-'):
        return 'gemini'
    
    # OpenRouter models (all others)
    return 'openrouter'

def clean_model_name(model_name: str) -> str:
    """Clean model name by removing provider prefixes."""
    if not model_name:
        return ""
    
    # Remove google/ prefix for Gemini models
    if model_name.startswith('google/'):
        return model_name.replace('google/', '')
    
    # Remove any other provider prefixes that might cause issues
    if model_name.startswith('openai/'):
        return model_name.replace('openai/', '')
    
    return model_name

# OpenRouter API Keys (can be multiple for round-robin)
OPENROUTER_API_KEYS = clean_api_keys(get_env_var("OPENROUTER_API_KEYS", ""))

# Gemini API Keys (can be multiple for round-robin)
GEMINI_API_KEYS = clean_api_keys(get_env_var("GEMINI_API_KEYS", ""))

# Default Models - use exact values from .env
DEFAULT_OPENROUTER_MODEL = get_env_var("DEFAULT_OPENROUTER_MODEL", "")
DEFAULT_GEMINI_MODEL = get_env_var("DEFAULT_GEMINI_MODEL", "")

# Agent-specific model overrides - use exact values from .env
MANAGER_MODEL = get_env_var("MANAGER_MODEL", DEFAULT_GEMINI_MODEL)
RESEARCHER_MODEL = get_env_var("RESEARCHER_MODEL", DEFAULT_GEMINI_MODEL)
CODER_MODEL = get_env_var("CODER_MODEL", DEFAULT_OPENROUTER_MODEL)
ANALYST_MODEL = get_env_var("ANALYST_MODEL", DEFAULT_OPENROUTER_MODEL)
CRITIC_MODEL = get_env_var("CRITIC_MODEL", DEFAULT_OPENROUTER_MODEL)

# API Configuration
OPENROUTER_API_URL = "https://openrouter.ai/api/v1"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"

# Timeout settings
REQUEST_TIMEOUT = 60
MAX_RETRIES = 3

# Workspace settings
WORKSPACE_BASE = "workspace"
TEMP_CODE_DIR = "temp_code"
OUTPUTS_DIR = "outputs"
LOGS_DIR = "logs"
DATA_DIR = "data"

# Browser Settings
BROWSER_HEADLESS = get_env_var("BROWSER_HEADLESS", "false").lower() == "true"
BROWSER_SLOW_MO = int(get_env_var("BROWSER_SLOW_MO", "1000"))
BROWSER_TIMEOUT = int(get_env_var("BROWSER_TIMEOUT", "30000"))
BROWSER_VIEWPORT_WIDTH = int(get_env_var("BROWSER_VIEWPORT_WIDTH", "1920"))
BROWSER_VIEWPORT_HEIGHT = int(get_env_var("BROWSER_VIEWPORT_HEIGHT", "1080"))
BROWSER_USER_AGENT = get_env_var("BROWSER_USER_AGENT", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# Web Research Settings
WEB_RESEARCH_MAX_PAGES = int(get_env_var("WEB_RESEARCH_MAX_PAGES", "5"))
WEB_RESEARCH_MAX_RETRIES = int(get_env_var("WEB_RESEARCH_MAX_RETRIES", "3"))
WEB_RESEARCH_DELAY_MIN = float(get_env_var("WEB_RESEARCH_DELAY_MIN", "1.0"))
WEB_RESEARCH_DELAY_MAX = float(get_env_var("WEB_RESEARCH_DELAY_MAX", "3.0"))
WEB_RESEARCH_SHOW_PROGRESS = get_env_var("WEB_RESEARCH_SHOW_PROGRESS", "true").lower() == "true"

# Search Engine Settings
SEARCH_ENGINE = get_env_var("SEARCH_ENGINE", "duckduckgo")
GOOGLE_API_KEY = get_env_var("GOOGLE_API_KEY", "")
GOOGLE_CSE_ID = get_env_var("GOOGLE_CSE_ID", "")

# File Output Settings
OUTPUT_FORMAT = get_env_var("OUTPUT_FORMAT", "markdown")
CREATE_SCREENSHOTS = get_env_var("CREATE_SCREENSHOTS", "true").lower() == "true"
SAVE_HTML_SOURCES = get_env_var("SAVE_HTML_SOURCES", "true").lower() == "true"

# Security settings
MAX_CODE_EXECUTION_TIME = int(get_env_var("MAX_CODE_EXECUTION_TIME", "30"))
ALLOWED_FILE_EXTENSIONS = get_env_var("ALLOWED_FILE_EXTENSIONS", ".py,.txt,.json,.csv,.md,.html").split(",")
MAX_FILE_SIZE_MB = int(get_env_var("MAX_FILE_SIZE_MB", "10"))

# Token settings
MAX_OUTPUT_TOKENS = int(get_env_var("MAX_OUTPUT_TOKENS", "64000"))

# Logging Settings
LOG_LEVEL = get_env_var("LOG_LEVEL", "INFO")
LOG_TO_FILE = get_env_var("LOG_TO_FILE", "true").lower() == "true"
LOG_FILE_PATH = get_env_var("LOG_FILE_PATH", "logs/deep_action_agent.log")

def validate_config():
    """Validate the configuration and print warnings for issues."""
    issues = []
    
    if not OPENROUTER_API_KEYS:
        issues.append("No OpenRouter API keys found")
    
    if not GEMINI_API_KEYS:
        issues.append("No Gemini API keys found")
    
    if not MANAGER_MODEL:
        issues.append("Manager model not configured")
    
    if not RESEARCHER_MODEL:
        issues.append("Researcher model not configured")
    
    if not CODER_MODEL:
        issues.append("Coder model not configured")
    
    if not ANALYST_MODEL:
        issues.append("Analyst model not configured")
    
    if not CRITIC_MODEL:
        issues.append("Critic model not configured")
    
    if issues:
        print("Configuration Issues Found:")
        for issue in issues:
            print(f"  - {issue}")
        print("\nPlease check your .env file and ensure all required variables are set.")
    else:
        print("Configuration validation passed!")
    
    return len(issues) == 0

# Validate configuration on import
if __name__ == "__main__":
    validate_config()


