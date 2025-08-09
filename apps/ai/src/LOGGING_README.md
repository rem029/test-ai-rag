# AI Service Logging

This document describes the custom logging system implemented for the AI service.

## Overview

The logging system provides:
- Session-based logging with unique log files for each conversation session
- Rich console formatting for development/debugging
- Clean text logging to files (stripped of formatting)
- Structured logging of different types of events (user inputs, AI responses, errors, etc.)

## Files

### `services/logger.py`
The main logger service that provides the `SessionLogger` class with methods for different types of logging.

### Updated Files
- `services/ai.py` - Updated to use the new logger throughout the AI processing pipeline
- `controller/message.py` - Updated to handle session management and logging initialization

## Usage

### Basic Usage in AI Service

```python
from services.logger import get_logger

# Get the global logger instance
logger = get_logger()

# Setup session logging (done automatically in stream_response_logic)
logger.setup_session_logging(session_id)

# Log various types of events
logger.log_user_input(session_id, "user message", has_image=True)
logger.log_ai_response("AI response text")
logger.log_error("Error message", "ERROR_TYPE")
```

### Session Management Functions

```python
from services.ai import initialize_session_logging, end_session_logging

# Initialize logging for a session
log_file_path = initialize_session_logging(session_id)

# End logging for a session  
end_session_logging(session_id, "reason")
```

## Logger Methods

### Core Methods
- `setup_session_logging(session_id)` - Creates session-specific log file
- `log_and_print(message, style, log_level)` - Logs to both console and file

### Specialized Logging Methods
- `log_user_input(session_id, input, has_image, image_info)` - Log user inputs
- `log_system_prompt(prompt)` - Log system prompts
- `log_recent_messages(messages)` - Log conversation history
- `log_ai_response_start()` - Mark start of AI response generation
- `log_ai_response(response, audio_file)` - Log complete AI responses
- `log_embedding_context(count)` - Log embedding retrieval info
- `log_error(message, error_type)` - Log errors with types
- `log_session_end(session_id, reason)` - Mark end of session

## Log File Format

Log files are created with the pattern: `ai_session_{session_id_8chars}_{timestamp}.log`

Example: `ai_session_a1b2c3d4_20250809_143022.log`

### Log File Structure
```
2025-08-09 14:30:22 | Session_a1b2c3d4 | INFO     | === AI Service Session Started ===
2025-08-09 14:30:22 | Session_a1b2c3d4 | INFO     | Session ID: a1b2c3d4-e5f6-7890-abcd-ef1234567890
2025-08-09 14:30:22 | Session_a1b2c3d4 | INFO     | USER INPUT: Hello, how are you?
2025-08-09 14:30:22 | Session_a1b2c3d4 | INFO     | EMBEDDING CONTEXT: Retrieved 3 relevant embeddings
2025-08-09 14:30:22 | Session_a1b2c3d4 | INFO     | AI RESPONSE: Starting to generate response
2025-08-09 14:30:23 | Session_a1b2c3d4 | INFO     | AI RESPONSE: Hello! I'm doing well, thank you for asking.
```

## Console Output

The console output includes Rich formatting with emojis and colors for better development experience:
- 🤖 AI responses
- 📄 Session info  
- ✅ Success messages
- ⚠️ Warnings
- ❌ Errors
- 🆔 Session IDs
- 📊 Statistics

## Testing

Run the test script to see the logging in action:

```bash
cd /home/rem029/test-ai-rag/apps/ai/src
python test_logger.py
```

This will demonstrate all logging features and create a sample log file.

## Migration from Test File

The logging functionality was migrated from `test_stream_response_with_audio.py` to provide:

1. **Separation of Concerns**: Logging logic is now in its own service
2. **Reusability**: Can be used across different parts of the application  
3. **Maintainability**: Centralized logging configuration and methods
4. **Production Ready**: Proper error handling and session management

## Integration Points

The logger integrates with:
- FastAPI endpoints via the message controller
- AI response streaming in `services/ai.py`
- Error handling throughout the application
- Session management for conversation tracking

## Configuration

The logger can be configured by modifying the `SessionLogger` class in `services/logger.py`:
- Change log directory location
- Modify log file naming pattern
- Adjust log formatting
- Configure Rich console settings
