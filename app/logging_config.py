import logging.config
import json
import os

def setup_logging(
    default_path: str = os.path.join(os.path.dirname(__file__), "../config/default_logging.json"),
    default_level: int = logging.INFO
):
    """Load logging configuration from JSON file and apply environment variable overrides."""
    path = default_path
    if os.path.exists(path):
        with open(path, 'rt', encoding='utf8') as f:
            config = json.load(f)

        # Override handler levels based on environment variables
        # FLASK_CONSOLE_LOG_LEVEL
        console_log_level = os.environ.get('FLASK_CONSOLE_LOG_LEVEL')
        if console_log_level and 'console' in config.get('handlers', {}):
            config['handlers']['console']['level'] = console_log_level.upper()

        # FLASK_FILE_LOG_LEVEL
        file_log_level = os.environ.get('FLASK_FILE_LOG_LEVEL')
        if file_log_level and 'file' in config.get('handlers', {}):
            config['handlers']['file']['level'] = file_log_level.upper()

        # Overall APP_LOG_LEVEL for the 'app' logger
        app_log_level = os.environ.get('FLASK_APP_LOG_LEVEL')
        if app_log_level and 'app' in config.get('loggers', {}):
            config['loggers']['app']['level'] = app_log_level.upper()

        # Root logger level (optional, but good to control)
        root_log_level = os.environ.get('FLASK_ROOT_LOG_LEVEL')
        if root_log_level and '' in config.get('loggers', {}):
            config['loggers']['']['level'] = root_log_level.upper()


        # Decide whether to use JSON formatter for console
        use_json_console = os.environ.get('FLASK_CONSOLE_JSON_LOGS', 'false').lower() == 'true'
        if use_json_console and 'console' in config.get('handlers', {}):
            config['handlers']['console']['formatter'] = 'json'

        # Decide whether to enable file logging based on env var
        log_file_path = os.environ.get('FLASK_LOG_FILE_PATH')
        if not log_file_path and 'file' in config.get('loggers', {}).get('', {}).get('handlers', []):
            # If FLASK_LOG_FILE_PATH is NOT set, remove 'file' handler from root logger
            config['loggers']['']['handlers'] = [
                h for h in config['loggers']['']['handlers'] if h != 'file'
            ]
            if 'app' in config.get('loggers', {}): # Also remove from 'app' logger if present
                 config['loggers']['app']['handlers'] = [
                    h for h in config['loggers']['app']['handlers'] if h != 'file'
                ]
            # Optionally remove the handler definition entirely if no one uses it
            if 'file' in config.get('handlers', {}):
                del config['handlers']['file']
        elif log_file_path and 'file' in config.get('handlers', {}):
            # If path IS set, update the filename
            config['handlers']['file']['filename'] = log_file_path
            # Ensure the directory exists
            log_dir = os.path.dirname(log_file_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir) # Add this to ensure the directory exists

        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)
        logging.getLogger().warning(f"Logging configuration file not found at {path}. Using basicConfig.")
