import os


def _load_local_dotenv() -> None:
    """
    Lightweight .env loader for local development.
    - Does not override existing environment variables.
    - Supports simple KEY=VALUE lines and ignores comments.
    """
    base_dir = os.path.abspath(os.path.dirname(__file__))
    env_path = os.path.join(base_dir, '.env')
    if not os.path.isfile(env_path):
        return

    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value
    except OSError:
        pass


_load_local_dotenv()


class Config:
    SECRET_KEY    = os.environ.get('SECRET_KEY') or 'skillgap-pro-secret-2026'
    BASE_DIR      = os.path.abspath(os.path.dirname(__file__))
    DATABASE_PATH = os.path.join(BASE_DIR, 'database', 'skillgap.db')
    NLP_MODEL_NAME = 'all-MiniLM-L6-v2'
    DEBUG         = True

    # AI Chatbot Configuration
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    CHATBOT_MODEL = os.environ.get('CHATBOT_MODEL') or 'gpt-3.5-turbo'

    # GitHub API (optional, but recommended to avoid rate limits)
    GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN') or os.environ.get('GITHUB_API_TOKEN') or ''

    # Email Configuration (Gmail)
    GMAIL_EMAIL = os.environ.get('GMAIL_EMAIL') or 'your-email@gmail.com'
    GMAIL_PASSWORD = os.environ.get('GMAIL_PASSWORD') or 'your-app-password'
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587

    # Upload limits (profile pictures, etc.)
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024  # 2MB
