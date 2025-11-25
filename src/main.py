"""
Architects Tool No.1 - AI Voice Orchestration

Professional voice transcription and AI-powered text processing.
Uses OpenAI Whisper API for transcription and GPT for text cleanup.

Usage:
    python -m src.main

Or after installation:
    architectstool
"""

import sys
import logging
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def setup_logging():
    """Configure application logging."""
    log_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    # Configure StreamHandler with UTF-8 encoding to handle Serbian characters
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(log_format))

    # Force UTF-8 encoding on the handler
    if hasattr(handler.stream, 'reconfigure'):
        handler.stream.reconfigure(encoding='utf-8', errors='replace')

    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[handler]
    )

    # Set third-party loggers to WARNING
    logging.getLogger("PIL").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def main():
    """Main entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)

    logger.info("=" * 50)
    logger.info("Architects Tool No.1 - AI Voice Orchestration")
    logger.info("=" * 50)

    try:
        # Import here to avoid issues before logging is set up
        from src.app import VoiceTypeApp

        # Create and run application
        app = VoiceTypeApp()
        app.run()

    except ImportError as e:
        logger.error(f"Missing dependency: {e}")
        logger.error("Please install requirements: pip install -r requirements.txt")
        sys.exit(1)

    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        sys.exit(0)

    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
