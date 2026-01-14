import os
import json
import logging
import logging.config
from pathlib import Path

def setup_logging(
    default_path: str = os.path.join(os.path.dirname(__file__), "../config/default_logging.json"),
    default_level: int = logging.INFO
):
    """
    Load logging configuration from JSON file and apply environment variable overrides.
    
    Production Logic:
      1. Tries to load JSON config.
      2. Overrides levels via Env Vars.
      3. Determines Log File Path:
         - IF FLASK_LOG_FILE_PATH is set -> Overrides JSON.
         - ELSE -> Uses JSON default.
      4. Ensures log directory exists. If not writable, disables file logging safely.
      5. Applies configuration.
    """
    path = Path(default_path)

    # ---------------------------------------------------------
    # 1️⃣ Load JSON Configuration
    # ---------------------------------------------------------
    if path.exists():
        try:
            with path.open('rt', encoding='utf8') as f:
                config = json.load(f)
        except Exception as e:
            # Malformed JSON -> Fallback
            logging.basicConfig(level=default_level)
            logging.getLogger().warning(f"Failed to load logging JSON from {path}: {e}. Using basicConfig.")
            return
    else:
        # Missing JSON -> Fallback
        logging.basicConfig(level=default_level)
        logging.getLogger().warning(f"Logging configuration file not found at {path}. Using basicConfig.")
        return

    # ---------------------------------------------------------
    # 2️⃣ Override Handler Levels (Env Vars)
    # ---------------------------------------------------------
    handlers = config.get('handlers', {})
    loggers = config.get('loggers', {})

    # Map Env Vars to Config Keys
    env_map = {
        'FLASK_CONSOLE_LOG_LEVEL': ('handlers', 'console'),
        'FLASK_FILE_LOG_LEVEL':    ('handlers', 'file'),
        'FLASK_APP_LOG_LEVEL':     ('loggers', 'app'),
        'FLASK_ROOT_LOG_LEVEL':    ('loggers', '')
    }

    for env_var, (section, key) in env_map.items():
        level = os.environ.get(env_var)
        if level and key in config.get(section, {}):
            config[section][key]['level'] = level.upper()

    # ---------------------------------------------------------
    # 3️⃣ Configure Console Formatter (JSON vs Text)
    # ---------------------------------------------------------
    use_json_console = os.environ.get('FLASK_CONSOLE_JSON_LOGS', 'false').lower() == 'true'
    if use_json_console and 'console' in handlers:
        handlers['console']['formatter'] = 'json'

    # ---------------------------------------------------------
    # 4️⃣ File Logging Path & Safety (The Fix)
    # ---------------------------------------------------------
    if 'file' in handlers:
        env_log_path = os.environ.get('FLASK_LOG_FILE_PATH')
        
        # Override filename if Env Var is set
        if env_log_path:
            handlers['file']['filename'] = env_log_path
        
        # Resolve the final path (whether from JSON or Env)
        log_file_path = Path(handlers['file']['filename'])
        
        try:
            # Ensure directory exists
            log_file_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            # PROD SAFETY: If we can't create the folder (e.g., Read-Only filesystem), 
            # remove the file handler to prevent crash during dictConfig.
            logging.basicConfig(level=default_level) # Temp setup to log the warning
            logging.getLogger().error(f"Cannot create log directory {log_file_path.parent}: {e}. Disabling file logging.")
            
            # Remove 'file' from all loggers to avoid runtime errors
            for logger in loggers.values():
                if 'handlers' in logger:
                    logger['handlers'] = [h for h in logger['handlers'] if h != 'file']
            # Remove the handler definition
            del handlers['file']

    # ---------------------------------------------------------
    # 5️⃣ Apply Final Configuration
    # ---------------------------------------------------------
    try:
        logging.config.dictConfig(config)
    except Exception as e:
        logging.basicConfig(level=default_level)
        logging.getLogger().exception(f"Failed to apply logging configuration: {e}")