import json
import logging
import logging.config
import os


def configure_logging():
    """
    Configure logging using logging.config to output to both file and standard output.
    Locally, only console logging is enabled.
    """
    try:
        # Load logging configuration from json file
        config_file = os.path.join(os.path.dirname(__file__), "logging.json")
        with open(config_file) as f_in:
            config = json.load(f_in)

        can_use_file_logging = False

        if os.path.exists("/app"):
            try:
                os.makedirs("/app/logs", exist_ok=True)
                can_use_file_logging = True
            except (OSError, PermissionError):
                pass

        if not can_use_file_logging:
            if "file" in config.get("root", {}).get("handlers", []):
                config["root"]["handlers"].remove("file")
            if "file" in config.get("handlers", {}):
                del config["handlers"]["file"]

        logging.config.dictConfig(config)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading logging config from {config_file}: {e}")
        raise
    except KeyError as e:
        print(f"Error in logging configuration: {e}")
        raise


# Initialize logging configuration
configure_logging()


def get_logger(name: str) -> logging.Logger:
    """
    Return a logger with the specified name.
    Args:
        name (str): The name of the logger.
    Returns:
        logging.Logger: A logger instance.
    """
    return logging.getLogger(name)
