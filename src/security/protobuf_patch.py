"""
CVE-2026-0994 Patch for protobuf json_format recursion depth bypass

This module patches google.protobuf.json_format to fix the recursion depth
bypass vulnerability in _ConvertAnyMessage. The issue is that nested Any
messages don't increment the recursion counter, allowing attackers to
bypass max_recursion_depth limits.

Usage:
    # Import this module BEFORE using protobuf json_format
    from src.security import protobuf_patch
    protobuf_patch.apply()

    # Then use protobuf normally
    from google.protobuf import json_format
    json_format.ParseDict(...)
"""

import functools
from typing import Any, Callable

_PATCH_APPLIED = False


def apply() -> bool:
    """
    Apply the CVE-2026-0994 security patch to protobuf json_format.

    Returns:
        True if patch was applied, False if already applied or not needed.
    """
    global _PATCH_APPLIED

    if _PATCH_APPLIED:
        return False

    try:
        from google.protobuf import json_format
    except ImportError:
        # protobuf not installed, nothing to patch
        return False

    # Get the _Parser class
    parser_class = json_format._Parser

    # Store original method
    original_convert_any = parser_class._ConvertAnyMessage

    @functools.wraps(original_convert_any)
    def patched_convert_any_message(self, value, message, path):
        """
        Patched _ConvertAnyMessage that properly tracks recursion depth.

        CVE-2026-0994: The original method calls _ConvertFieldValuePair
        without incrementing recursion_depth, bypassing the depth limit.
        """
        # Increment recursion depth BEFORE processing nested Any
        self.recursion_depth += 1

        if self.recursion_depth > self.max_recursion_depth:
            raise json_format.ParseError(
                'Message too deep. Max recursion depth is {0}'.format(
                    self.max_recursion_depth
                )
            )

        try:
            # Call original method
            return original_convert_any(self, value, message, path)
        finally:
            # Always decrement, even on error
            self.recursion_depth -= 1

    # Apply the patch
    parser_class._ConvertAnyMessage = patched_convert_any_message

    _PATCH_APPLIED = True
    return True


def is_applied() -> bool:
    """Check if the patch has been applied."""
    return _PATCH_APPLIED


def verify_patch() -> dict:
    """
    Verify the patch works by testing with nested Any messages.

    Returns:
        Dict with verification results.
    """
    results = {
        'patch_applied': _PATCH_APPLIED,
        'vulnerability_mitigated': False,
        'error': None
    }

    if not _PATCH_APPLIED:
        results['error'] = 'Patch not applied. Call apply() first.'
        return results

    try:
        from google.protobuf import json_format
        from google.protobuf import any_pb2
        from google.protobuf import struct_pb2

        # Create a deeply nested structure that would bypass the original limit
        def create_nested_any(depth: int) -> dict:
            if depth <= 0:
                return {
                    '@type': 'type.googleapis.com/google.protobuf.Value',
                    'value': {'stringValue': 'test'}
                }
            return {
                '@type': 'type.googleapis.com/google.protobuf.Any',
                'value': create_nested_any(depth - 1)
            }

        # Try to parse with depth exceeding limit
        any_msg = any_pb2.Any()
        nested_json = create_nested_any(150)  # Exceeds default 100 limit

        try:
            json_format.ParseDict(nested_json, any_msg, max_recursion_depth=100)
            results['vulnerability_mitigated'] = False
            results['error'] = 'Nested Any bypass still possible'
        except json_format.ParseError as e:
            if 'too deep' in str(e).lower():
                results['vulnerability_mitigated'] = True
            else:
                results['error'] = str(e)

    except Exception as e:
        results['error'] = f'Verification failed: {e}'

    return results


# Auto-apply on import if environment variable is set
import os
if os.environ.get('SCBE_AUTO_PATCH_PROTOBUF', '').lower() in ('1', 'true', 'yes'):
    apply()
