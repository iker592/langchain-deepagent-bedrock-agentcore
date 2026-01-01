from .logger import get_logger

logger = get_logger(__name__)


def event_loop_tracker(**kwargs):
    """Callback handler for event loop tracking"""

    # Track event loop lifecycle
    if kwargs.get("init_event_loop", False):
        logger.debug("🔄 Event loop initialized")
    elif kwargs.get("start_event_loop", False):
        logger.debug("▶️ Event loop cycle starting")
    elif kwargs.get("start", False):
        logger.debug("📝 New cycle started")
    elif "message" in kwargs:
        logger.debug(f"📬 New message created: {kwargs['message']['role']}")
    elif kwargs.get("complete", False):
        logger.debug("✅ Cycle completed")
    elif kwargs.get("force_stop", False):
        logger.debug(f"🛑 Event loop force-stopped: {kwargs.get('force_stop_reason', 'unknown')}")

    # Track tool usage
    if "current_tool_use" in kwargs and kwargs["current_tool_use"].get("name"):
        tool_name = kwargs["current_tool_use"]["name"]
        logger.debug(f"🔧 Using tool: {tool_name}")

    # Track tokens
    if "data" in kwargs:
        logger.debug(f"📟 Token: {kwargs['data']}")
