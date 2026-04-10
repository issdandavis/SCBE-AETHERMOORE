import asyncio
import builtins

from hydra.head import HydraHead
from hydra.spine import HydraSpine


def test_hydra_head_connect_survives_unicode_console_fail(monkeypatch):
    real_print = builtins.print

    def flaky_print(*args, **kwargs):
        text = " ".join(str(arg) for arg in args)
        if "HYDRA HEAD CONNECTED" in text:
            raise UnicodeEncodeError("charmap", text, 0, len(text), "character maps to <undefined>")
        return real_print(*args, **kwargs)

    monkeypatch.setattr(builtins, "print", flaky_print)

    spine = HydraSpine(use_dual_lattice=False, use_switchboard=False)
    head = HydraHead(ai_type="hf", model="Qwen/Qwen2.5-7B-Instruct", callsign="KO-scout")

    connected = asyncio.run(head.connect(spine))

    assert connected is True
    assert head.status.value == "connected"
    assert head.head_id in spine.heads
