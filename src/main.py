"""Entry point for the application"""

import sys
import argparse
from src.app import InstancepediaApp
from src.config.settings import Settings
from src.debug import DebugLog


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="EC2 Instance Type Browser")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with debug pane"
    )
    args = parser.parse_args()

    try:
        settings = Settings()
        
        # Enable debug if requested
        if args.debug:
            DebugLog.enable()
        
        app = InstancepediaApp(settings, debug=args.debug)
        app.run()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

