"""Test actual Textual app exit to reproduce unclosed session warnings"""

import asyncio
import pytest
import warnings
import gc
import sys
import subprocess
import time


class TestTextualAppExit:
    """Test actual Textual app behavior"""

    def test_textual_app_exit_with_pricing_worker(self):
        """Run a minimal Textual app that creates pricing worker and exits"""
        test_script = '''
import asyncio
import warnings
import sys

warnings.filterwarnings("always", category=ResourceWarning)

# Make sure warnings go to stderr
import logging
logging.captureWarnings(True)

from textual.app import App
from textual.widgets import Static
from textual.screen import Screen

from src.services.async_aws_client import AsyncAWSClient
from src.services.async_pricing_service import AsyncPricingService


class TestScreen(Screen):
    def __init__(self):
        super().__init__()
        self._pricing_worker = None
        self._async_client = None

    def compose(self):
        yield Static("Testing...")

    def on_mount(self):
        # Start pricing fetch like InstanceDetail does
        async def fetch_pricing():
            try:
                self._async_client = AsyncAWSClient(
                    "us-east-1",
                    connect_timeout=10,
                    read_timeout=60,
                    pricing_timeout=90,
                    max_pool_connections=50
                )
                async with self._async_client as client:
                    pricing_service = AsyncPricingService(client)
                    async with client.get_pricing_client() as pricing:
                        # Simulate work that will be cancelled on exit
                        await asyncio.sleep(10)
            except asyncio.CancelledError:
                # This is what happens when app exits
                raise

        self._pricing_worker = self.app.run_worker(fetch_pricing, exit_on_error=False)

        # Exit after short delay
        self.set_timer(0.3, self._do_exit)

    def _do_exit(self):
        self.app.exit()

    def on_unmount(self):
        if self._pricing_worker and not self._pricing_worker.is_finished:
            self._pricing_worker.cancel()


class TestApp(App):
    def on_mount(self):
        self.push_screen(TestScreen())


if __name__ == "__main__":
    app = TestApp()
    app.run()
'''
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            capture_output=True,
            text=True,
            timeout=15,
            cwd="/Users/pfrederiksen/Documents/code/instancepedia",
            env={**dict(list(__import__('os').environ.items())), "PYTHONWARNINGS": "always"}
        )

        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        print(f"Return code: {result.returncode}")

        # Check for unclosed warnings
        has_unclosed = "Unclosed" in result.stderr or "Unclosed" in result.stdout
        if has_unclosed:
            pytest.fail(f"Found unclosed session warnings:\n{result.stderr}")

    def test_textual_app_exit_quick(self):
        """Run Textual app with very quick exit"""
        test_script = '''
import asyncio
import warnings
import sys
import os

# Force all warnings to stderr
warnings.filterwarnings("always", category=ResourceWarning)
os.environ["PYTHONWARNINGS"] = "always::ResourceWarning"

from textual.app import App
from textual.widgets import Static
from textual.screen import Screen

from src.services.async_aws_client import AsyncAWSClient


class TestScreen(Screen):
    def compose(self):
        yield Static("Testing...")

    async def on_mount(self):
        # Create client directly (not in worker)
        self._client = AsyncAWSClient("us-east-1")

        # Get pricing client to create underlying session
        async with self._client.get_pricing_client() as pricing:
            pass

        # Exit immediately
        self.set_timer(0.1, lambda: self.app.exit())

    async def on_unmount(self):
        # Try to clean up
        if hasattr(self, "_client"):
            await self._client.close()


class TestApp(App):
    def on_mount(self):
        self.push_screen(TestScreen())


if __name__ == "__main__":
    app = TestApp()
    app.run()
'''
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            capture_output=True,
            text=True,
            timeout=15,
            cwd="/Users/pfrederiksen/Documents/code/instancepedia",
            env={**dict(list(__import__('os').environ.items())), "PYTHONWARNINGS": "always::ResourceWarning"}
        )

        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        print(f"Return code: {result.returncode}")

        has_unclosed = "Unclosed" in result.stderr or "Unclosed" in result.stdout
        if has_unclosed:
            pytest.fail(f"Found unclosed session warnings:\n{result.stderr}")

    def test_real_instance_detail_pattern(self):
        """Test the exact pattern used in instance_detail.py"""
        test_script = '''
import asyncio
import warnings
import sys
import gc

warnings.filterwarnings("always", category=ResourceWarning)

from textual.app import App
from textual.widgets import Static
from textual.screen import Screen

from src.services.async_aws_client import AsyncAWSClient
from src.services.async_pricing_service import AsyncPricingService


class TestScreen(Screen):
    def __init__(self):
        super().__init__()
        self._pricing_worker = None

    def compose(self):
        yield Static("Testing the exact instance_detail pattern...")

    def on_mount(self):
        self._fetch_pricing_if_needed()
        # Schedule exit
        self.set_timer(0.5, lambda: self.app.exit())

    def _fetch_pricing_if_needed(self):
        """Exact copy of the pattern from instance_detail.py"""
        async def fetch_pricing():
            try:
                region = "us-east-1"
                async with AsyncAWSClient(
                    region,
                    None,  # profile
                    connect_timeout=10,
                    read_timeout=60,
                    pricing_timeout=90,
                    max_pool_connections=50
                ) as async_client:
                    pricing_service = AsyncPricingService(async_client)

                    # Get pricing client to simulate fetching
                    async with async_client.get_pricing_client() as pricing:
                        # Simulate work that will be interrupted
                        await asyncio.sleep(10)

                # Context manager exit should handle cleanup
            except asyncio.CancelledError:
                # Re-raise to let the worker handle it - EXACT pattern from instance_detail.py
                raise
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)

        self._pricing_worker = self.app.run_worker(fetch_pricing, exit_on_error=False)

    def on_unmount(self):
        """Exact copy from instance_detail.py"""
        if self._pricing_worker is not None and not self._pricing_worker.is_finished:
            try:
                self._pricing_worker.cancel()
            except Exception:
                pass


class TestApp(App):
    def on_mount(self):
        self.push_screen(TestScreen())


if __name__ == "__main__":
    app = TestApp()
    app.run()

    # Force GC after app exits
    gc.collect()
    import time
    time.sleep(0.5)
    gc.collect()
'''
        result = subprocess.run(
            [sys.executable, "-c", test_script],
            capture_output=True,
            text=True,
            timeout=20,
            cwd="/Users/pfrederiksen/Documents/code/instancepedia",
            env={**dict(list(__import__('os').environ.items())), "PYTHONWARNINGS": "always::ResourceWarning"}
        )

        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        print(f"Return code: {result.returncode}")

        has_unclosed = "Unclosed" in result.stderr or "Unclosed" in result.stdout
        if has_unclosed:
            pytest.fail(f"Found unclosed session warnings:\n{result.stderr}")
        else:
            print("NO UNCLOSED WARNINGS DETECTED")
