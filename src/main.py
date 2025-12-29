"""Entry point for the application"""

import sys
from src.cli.parser import parse_args
from src.cli.commands import run_cli
from src.app import InstancepediaApp
from src.config.settings import Settings
from src.debug import DebugLog


def main():
    """Main entry point"""
    # Parse arguments using CLI parser (which handles both CLI and TUI modes)
    args = parse_args()
    
    # Check if we should run in TUI mode
    # TUI mode if:
    # 1. --tui flag is explicitly set, OR
    # 2. No command is provided (backward compatibility)
    if args.tui or not args.command:
        # TUI mode
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
    else:
        # CLI mode
        exit_code = run_cli(args)
        sys.exit(exit_code)


if __name__ == "__main__":
    main()

