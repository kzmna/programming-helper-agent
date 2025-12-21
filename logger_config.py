"""Comprehensive logging configuration for multi-agent system."""
import logging
import sys
from datetime import datetime
from pathlib import Path
import json
from typing import Any, Dict


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for terminal output."""
    
    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'
    }
    
    COMPONENT_COLORS = {
        'AGENT': '\033[94m',      # Light blue
        'TOOL': '\033[95m',       # Light magenta
        'LLM': '\033[93m',        # Light yellow
        'STATE': '\033[96m',      # Light cyan
        'MEMORY': '\033[92m',     # Light green
    }
    
    def format(self, record):
        # Color the log level
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.COLORS['RESET']}"
        
        # Ensure component field exists (for third-party libraries)
        if not hasattr(record, 'component'):
            record.component = 'EXTERNAL'
        
        # Color component tags
        component = record.component
        if component in self.COMPONENT_COLORS:
            record.component = f"{self.COMPONENT_COLORS[component]}{component}{self.COLORS['RESET']}"
        
        return super().format(record)


def setup_logging(log_level: str = "INFO", log_file: str = None):
    """Setup comprehensive logging for the multi-agent system.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        log_file: Optional file path for logging output
    """
    # Create logs directory
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Generate log file name if not provided
    if log_file is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"multiagent_{timestamp}.log"
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Console handler with colors
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = ColoredFormatter(
        '%(asctime)s | %(levelname)-8s | %(component)-8s | %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)
    
    # File handler with detailed format
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(component)-8s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("openai").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("arxiv").setLevel(logging.WARNING)  # Suppress arxiv HTTP logs
    
    return log_file


class AgentLogger:
    """Specialized logger for agent operations."""
    
    def __init__(self, agent_name: str):
        self.logger = logging.getLogger(f"agent.{agent_name}")
        self.agent_name = agent_name
    
    def agent_started(self, state: Dict[str, Any]):
        """Log when an agent starts processing."""
        msg_count = len(state.get("messages", []))
        self.logger.info(
            f"🤖 {self.agent_name} started | Messages: {msg_count}",
            extra={"component": "AGENT"}
        )
    
    def agent_finished(self, state: Dict[str, Any]):
        """Log when an agent finishes processing."""
        msg_count = len(state.get("messages", []))
        self.logger.info(
            f"✅ {self.agent_name} finished | Messages: {msg_count}",
            extra={"component": "AGENT"}
        )
    
    def tool_called(self, tool_name: str, tool_input: Dict[str, Any]):
        """Log tool invocation."""
        # Log full input at INFO level
        input_str = json.dumps(tool_input, indent=2, default=str) if isinstance(tool_input, dict) else str(tool_input)
        self.logger.info(
            f"🔧 Tool called: {tool_name}",
            extra={"component": "TOOL"}
        )
        self.logger.info(
            f"   Input: {input_str}",
            extra={"component": "TOOL"}
        )
    
    def tool_result(self, tool_name: str, result: Any, success: bool = True):
        """Log tool result."""
        status = "✅" if success else "❌"
        # Log full result at INFO level
        result_str = json.dumps(result, indent=2, default=str) if isinstance(result, (dict, list)) else str(result)
        # Truncate only if extremely long (over 5000 chars)
        if len(result_str) > 5000:
            result_str = result_str[:5000] + f"\n... (truncated, total length: {len(result_str)} chars)"
        self.logger.info(
            f"{status} Tool result: {tool_name}",
            extra={"component": "TOOL"}
        )
        self.logger.info(
            f"   Result: {result_str}",
            extra={"component": "TOOL"}
        )
    
    def llm_call(self, prompt: str, model: str):
        """Log LLM invocation."""
        # Log full prompt at INFO level
        prompt_str = prompt if prompt else "N/A"
        # Truncate only if extremely long (over 10000 chars)
        if len(prompt_str) > 10000:
            prompt_str = prompt_str[:10000] + f"\n... (truncated, total length: {len(prompt_str)} chars)"
        self.logger.info(
            f"🧠 LLM call | Model: {model}",
            extra={"component": "LLM"}
        )
        self.logger.info(
            f"   Prompt: {prompt_str}",
            extra={"component": "LLM"}
        )
    
    def llm_response(self, response: str, tokens: int = None):
        """Log LLM response."""
        # Log full response at INFO level
        response_str = response if response else "N/A"
        token_info = f" | Tokens: {tokens}" if tokens else ""
        # Truncate only if extremely long (over 10000 chars)
        if len(response_str) > 10000:
            response_str = response_str[:10000] + f"\n... (truncated, total length: {len(response_str)} chars)"
        self.logger.info(
            f"💬 LLM response{token_info}",
            extra={"component": "LLM"}
        )
        self.logger.info(
            f"   Response: {response_str}",
            extra={"component": "LLM"}
        )
    
    def state_change(self, description: str, state_data: Dict[str, Any] = None):
        """Log state changes."""
        self.logger.info(
            f"📊 State change: {description}",
            extra={"component": "STATE"}
        )
        if state_data:
            self.logger.debug(
                f"State data: {json.dumps(state_data, indent=2, default=str)}",
                extra={"component": "STATE"}
            )
    
    def handoff(self, from_agent: str, to_agent: str, context: str):
        """Log agent handoffs."""
        self.logger.info(
            f"🔄 Handoff: {from_agent} → {to_agent} | Context: {context}",
            extra={"component": "AGENT"}
        )
    
    def memory_operation(self, operation: str, details: str):
        """Log memory/checkpoint operations."""
        self.logger.info(
            f"💾 Memory {operation}: {details}",
            extra={"component": "MEMORY"}
        )
    
    def error(self, error_msg: str, exception: Exception = None):
        """Log errors."""
        self.logger.error(
            f"❌ Error: {error_msg}",
            extra={"component": "AGENT"},
            exc_info=exception
        )


def get_agent_logger(agent_name: str) -> AgentLogger:
    """Get a logger for a specific agent.
    
    Args:
        agent_name: Name of the agent
        
    Returns:
        AgentLogger instance
    """
    return AgentLogger(agent_name)


# System-wide logger
def log_system(message: str, level: str = "INFO"):
    """Log system-level messages."""
    logger = logging.getLogger("system")
    log_func = getattr(logger, level.lower())
    log_func(message, extra={"component": "SYSTEM"})