"""Tests for aether_ide.chat."""
import sys
sys.path.insert(0, ".")
sys.path.insert(0, "src")

from src.aether_ide.chat import IDEChat, ChatMessage


def test_chat_send():
    chat = IDEChat()
    msg = chat.send("hello world", tongue="KO")
    assert msg.content == "hello world"
    assert msg.tongue == "KO"
    assert msg.role == "assistant"


def test_chat_history():
    chat = IDEChat()
    chat.send("msg1")
    chat.send("msg2")
    chat.send("msg3")
    history = chat.get_history(limit=2)
    assert len(history) == 2
    assert history[-1].content == "msg3"


def test_chat_clear():
    chat = IDEChat()
    chat.send("msg1")
    chat.clear()
    assert chat.message_count == 0


def test_chat_message_count():
    chat = IDEChat()
    assert chat.message_count == 0
    chat.send("hello")
    assert chat.message_count == 1
