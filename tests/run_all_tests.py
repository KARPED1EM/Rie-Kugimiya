#!/usr/bin/env python
"""Run all tests"""

import sys
import os
import asyncio
import traceback

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def run_sync_test(test_module_name, test_function_name):
    """Run a synchronous test"""
    try:
        module = __import__(f'tests.{test_module_name}', fromlist=[test_function_name])
        test_func = getattr(module, test_function_name)
        test_func()
        return True
    except Exception as e:
        print(f"❌ {test_module_name}.{test_function_name} failed:")
        print(f"   {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        return False


async def run_async_test(test_module_name, test_function_name):
    """Run an asynchronous test"""
    try:
        module = __import__(f'tests.{test_module_name}', fromlist=[test_function_name])
        test_func = getattr(module, test_function_name)
        await test_func()
        return True
    except Exception as e:
        print(f"❌ {test_module_name}.{test_function_name} failed:")
        print(f"   {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        return False


async def main():
    print("\n" + "=" * 70)
    print(" " * 20 + "RUNNING ALL TESTS")
    print("=" * 70 + "\n")

    all_passed = True

    # Configuration tests (sync)
    print("📋 Configuration Tests")
    print("-" * 70)
    from tests.test_config import run_all_tests as test_config
    try:
        test_config()
    except Exception as e:
        print(f"❌ Configuration tests failed: {e}")
        traceback.print_exc()
        all_passed = False
    print()

    # Database tests (sync)
    print("💾 Database Tests")
    print("-" * 70)
    from tests.test_database import run_all_tests as test_database
    try:
        test_database()
    except Exception as e:
        print(f"❌ Database tests failed: {e}")
        traceback.print_exc()
        all_passed = False
    print()

    # Message service tests (async)
    print("📨 Message Service Tests")
    print("-" * 70)
    from tests.test_message_service import run_all_tests as test_message_service
    try:
        await test_message_service()
    except Exception as e:
        print(f"❌ Message service tests failed: {e}")
        traceback.print_exc()
        all_passed = False
    print()

    # Behavior system tests (sync)
    print("🎭 Behavior System Tests")
    print("-" * 70)
    from tests.test_behavior_system import run_all_tests as test_behavior
    try:
        test_behavior()
    except Exception as e:
        print(f"❌ Behavior system tests failed: {e}")
        traceback.print_exc()
        all_passed = False
    print()

    # WebSocket manager tests (async)
    print("🔌 WebSocket Manager Tests")
    print("-" * 70)
    from tests.test_websocket_manager import run_all_tests as test_websocket
    try:
        await test_websocket()
    except Exception as e:
        print(f"❌ WebSocket manager tests failed: {e}")
        traceback.print_exc()
        all_passed = False
    print()

    # Integration tests (async)
    print("🔗 Integration Tests")
    print("-" * 70)
    from tests.test_integration import run_all_tests as test_integration
    try:
        await test_integration()
    except Exception as e:
        print(f"❌ Integration tests failed: {e}")
        traceback.print_exc()
        all_passed = False
    print()

    # Final summary
    print("=" * 70)
    if all_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED - Please review the output above")
    print("=" * 70)

    return 0 if all_passed else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
