import os
import re
import logging
from datetime import datetime
from typing import Optional
from rich.console import Console
from rich.logging import RichHandler


class SessionLogger:
    """
    A custom logger service for managing session-based logging with Rich formatting.
    """
    
    def __init__(self, logs_dir: str = "logs"):
        self.logs_dir = logs_dir
        self.session_logger: Optional[logging.Logger] = None
        self.log_file_path: Optional[str] = None
        self.console = Console(record=True)
        
        # Create logs directory if it doesn't exist
        os.makedirs(self.logs_dir, exist_ok=True)
        
        # Set up beautiful logging with Rich
        logging.basicConfig(
            level=logging.INFO,
            format="%(message)s",
            handlers=[RichHandler(console=self.console, rich_tracebacks=True)]
        )
        self.logger = logging.getLogger("AIService")

    def setup_session_logging(self, session_id: str) -> str:
        """
        Set up logging for a specific session.
        Creates a session-specific log file and configures logging.
        
        Args:
            session_id: The unique session identifier
            
        Returns:
            The path to the created log file
        """
        # Create session-specific log filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f"ai_session_{session_id[:8]}_{timestamp}.log"
        self.log_file_path = os.path.join(self.logs_dir, log_filename)
        
        # Create session logger
        self.session_logger = logging.getLogger(f"Session_{session_id[:8]}")
        self.session_logger.setLevel(logging.INFO)
        
        # Remove existing handlers
        self.session_logger.handlers.clear()
        
        # Create file handler for session logs
        file_handler = logging.FileHandler(self.log_file_path, encoding='utf-8')
        file_formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)-8s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.session_logger.addHandler(file_handler)
        
        # Log session start
        self.session_logger.info(f"=== AI Service Session Started ===")
        self.session_logger.info(f"Session ID: {session_id}")
        self.session_logger.info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.session_logger.info(f"Log File: {self.log_file_path}")
        self.session_logger.info("=" * 50)
        
        return self.log_file_path

    def log_and_print(self, message: str, style: str = "white", log_level: str = "info"):
        """
        Print to console with Rich formatting AND log to session file.
        
        Args:
            message: The message to log and print
            style: Rich style for console output (not used in file logging)
            log_level: The logging level (info, warning, error)
        """
        # Print to console with Rich formatting
        self.console.print(message)
        
        # Log to session file (strip Rich formatting for clean log)
        if self.session_logger:
            # Remove Rich markup for clean file logging
            clean_message = re.sub(r'\[.*?\]', '', message)
            clean_message = re.sub(r'[🤖📁✅❌🔊🎵⚠️💭📷🖼️🚫💤📸─]', '', clean_message).strip()
            
            if log_level.lower() == "info":
                self.session_logger.info(clean_message)
            elif log_level.lower() == "warning":
                self.session_logger.warning(clean_message)
            elif log_level.lower() == "error":
                self.session_logger.error(clean_message)

    def log_user_input(self, session_id: str, user_input: str, has_image: bool = False, image_info: str = ""):
        """
        Log user input with session information.
        
        Args:
            session_id: The session identifier
            user_input: The user's input text
            has_image: Whether the request includes an image
            image_info: Additional image information
        """
        if self.session_logger:
            self.session_logger.info(f"USER INPUT: {user_input}")
            if has_image:
                self.session_logger.info(f"IMAGE ATTACHED: {image_info}")

    def log_system_prompt(self, system_prompt: str):
        """
        Log the system prompt being used.
        
        Args:
            system_prompt: The system prompt content
        """
        if self.session_logger:
            self.session_logger.info(f"SYSTEM PROMPT: {system_prompt[:200]}..." if len(system_prompt) > 200 else f"SYSTEM PROMPT: {system_prompt}")

    def log_recent_messages(self, messages: list):
        """
        Log recent messages from conversation history.
        
        Args:
            messages: List of recent messages
        """
        if self.session_logger:
            self.session_logger.info("RECENT MESSAGES:")
            for msg in messages:
                role = msg.get("role", "unknown")
                content = msg.get("message", msg.get("content", ""))
                self.session_logger.info(f"  {role.upper()}: {content}")

    def log_ai_response_start(self):
        """Log the start of AI response streaming."""
        if self.session_logger:
            self.session_logger.info("AI RESPONSE: Starting to generate response")

    def log_ai_response(self, response: str, audio_file_path: Optional[str] = None):
        """
        Log the complete AI response.
        
        Args:
            response: The AI response text
            audio_file_path: Path to generated audio file, if any
        """
        if self.session_logger:
            # Clean response text by removing audio markers
            clean_response = re.sub(r'\[AUDIO_FILE:.*?\]', '', response).strip()
            self.session_logger.info(f"AI RESPONSE: {clean_response}")
            
            if audio_file_path:
                self.session_logger.info(f"AUDIO FILE GENERATED: {audio_file_path}")

    def log_embedding_context(self, embedding_count: int):
        """
        Log information about embedding context retrieval.
        
        Args:
            embedding_count: Number of embeddings retrieved
        """
        if self.session_logger:
            self.session_logger.info(f"EMBEDDING CONTEXT: Retrieved {embedding_count} relevant embeddings")

    def log_error(self, error_message: str, error_type: str = "ERROR"):
        """
        Log error messages.
        
        Args:
            error_message: The error message
            error_type: The type of error
        """
        if self.session_logger:
            self.session_logger.error(f"{error_type}: {error_message}")
        
        # Also log to console with Rich formatting
        self.console.print(f"❌ [red]{error_type}:[/red] [yellow]{error_message}[/yellow]")

    def log_session_end(self, session_id: str, reason: str = "Normal termination"):
        """
        Log the end of a session.
        
        Args:
            session_id: The session identifier
            reason: Reason for session termination
        """
        if self.session_logger:
            self.session_logger.info(f"=== Session {session_id[:8]} ended: {reason} ===")
            self.session_logger.info(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            self.session_logger.info("=" * 50)

    def get_log_file_path(self) -> Optional[str]:
        """
        Get the current log file path.
        
        Returns:
            The path to the current log file, or None if not set up
        """
        return self.log_file_path


# Global logger instance
session_logger_instance = SessionLogger()


def get_logger() -> SessionLogger:
    """
    Get the global session logger instance.
    
    Returns:
        The SessionLogger instance
    """
    return session_logger_instance
