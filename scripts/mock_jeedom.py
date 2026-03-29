#!/usr/bin/env python3
"""Mock Jeedom JSON-RPC server for Bran demo.

Standalone CLI wrapper. The actual server logic lives in bot.bran.mock.
Run: uv run python scripts/mock_jeedom.py
"""

from bot.bran.mock import main

if __name__ == "__main__":
    main()
