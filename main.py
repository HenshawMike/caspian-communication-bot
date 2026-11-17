"""Project Caspian Agent entry point."""

import sys
import signal
import argparse
from agent.config import settings
from agent.logging_config import logger
from database.models import initialize_database
from agent.orchestrator import orchestrator
from agent.background_runner import background_runner


def handle_shutdown(signum, frame):
    """Graceful shutdown hook for container SIGTERM / SIGINT signals."""
    logger.info(f"Received termination signal ({signum}). Stopping background services...")
    background_runner.stop()
    sys.exit(0)


def run_cli_interactive():
    """Interactive diagnostic loop for testing the agent without Telegram."""
    print("====================================================")
    print("Project Caspian Research Communications Agent (CLI)")
    print("====================================================")
    print("Type 'exit' or 'quit' to quit.\n")

    user_id = settings.telegram_authorized_user_id or "cli_admin"

    while True:
        try:
            prompt = input("You > ").strip()
            if not prompt:
                continue
            if prompt.lower() in ("exit", "quit"):
                print("Exiting agent.")
                break

            result = orchestrator.process_message(user_message=prompt, user_id=user_id)
            if result["success"]:
                skill = result["skill"]
                print(f"\n[Agent] Activated Skill: {skill['name']}")
                print(f"[Agent] Permissible Tools: {', '.join(skill['available_tools'])}")
                print(f"[Agent] Status: {result['message']}\n")
            else:
                print(f"\n[Agent] {result['message']}\n")

        except (KeyboardInterrupt, EOFError):
            print("\nExiting agent.")
            break
        except Exception as e:
            print(f"\n[Error] {e}\n")


def run_telegram_bot():
    """Start the private Telegram bot alongside background worker."""
    from telegram_bot.bot import create_bot
    if not settings.telegram_bot_token:
        logger.error("TELEGRAM_BOT_TOKEN not configured in environment or .env file.")
        print("Error: TELEGRAM_BOT_TOKEN is missing. Please configure it in .env or run with --cli.")
        sys.exit(1)

    # Start background polling runner
    background_runner.start()
    background_runner.update_heartbeat(status="HEALTHY")

    bot = create_bot()
    logger.info("Initializing Telegram bot and background services...")
    try:
        bot.run()
    finally:
        background_runner.stop()


def run_worker_only():
    """Run standalone background worker for scheduling and intelligence sweeps."""
    import time
    logger.info("Starting standalone background polling worker...")
    background_runner.start()
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Stopping worker...")
    finally:
        background_runner.stop()


def main():
    signal.signal(signal.SIGINT, handle_shutdown)
    signal.signal(signal.SIGTERM, handle_shutdown)

    parser = argparse.ArgumentParser(description="Project Caspian Agent")
    parser.add_argument("--cli", action="store_true", help="Run interactive CLI interface instead of Telegram")
    parser.add_argument("--worker-only", action="store_true", help="Run standalone background scheduler/worker only")
    args = parser.parse_args()

    # Ensure database is initialized
    initialize_database()

    if args.worker_only:
        run_worker_only()
    elif args.cli or not settings.telegram_bot_token:
        if not settings.telegram_bot_token and not args.cli:
            logger.info("No TELEGRAM_BOT_TOKEN found. Launching in CLI mode.")
        run_cli_interactive()
    else:
        run_telegram_bot()


if __name__ == "__main__":
    main()
