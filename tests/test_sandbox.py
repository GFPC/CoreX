"""
Unit tests for GFP CoreX Plugin Sandbox static AST validation.
"""

import pytest
from src.gfpcorex.plugins.sandbox import PluginSandbox, PluginSecurityChecker


def test_sandbox_allows_safe_code():
    safe_code = """
def calculate_discount(price, ratio):
    return price * (1.0 - ratio)

def hello(name):
    return f"Hello, {name}!"
"""
    is_safe, violations = PluginSandbox.validate_code(safe_code)
    assert is_safe is True
    assert len(violations) == 0


def test_sandbox_blocks_os_import():
    malicious_code = """
import os

def pwn():
    os.system("echo hacked")
"""
    is_safe, violations = PluginSandbox.validate_code(malicious_code)
    assert is_safe is False
    assert any("restricted module 'os'" in v for v in violations)


def test_sandbox_blocks_from_import():
    malicious_code = """
from subprocess import Popen

def run_cmd():
    Popen(["ls"])
"""
    is_safe, violations = PluginSandbox.validate_code(malicious_code)
    assert is_safe is False
    assert any("restricted module 'subprocess'" in v for v in violations)


def test_sandbox_blocks_eval_exec():
    malicious_code = """
def dynamic_eval(expr):
    return eval(expr)
"""
    is_safe, violations = PluginSandbox.validate_code(malicious_code)
    assert is_safe is False
    assert any("builtin function 'eval()'" in v for v in violations)


def test_sandbox_blocks_open():
    malicious_code = """
def read_secret():
    with open("/etc/passwd", "r") as f:
        return f.read()
"""
    is_safe, violations = PluginSandbox.validate_code(malicious_code)
    assert is_safe is False
    assert any("builtin function 'open()'" in v for v in violations)


def test_sandbox_handles_syntax_error():
    invalid_code = "def broken_func("
    is_safe, violations = PluginSandbox.validate_code(invalid_code)
    assert is_safe is False
    assert any("Syntax Error" in v for v in violations)
