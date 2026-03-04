from pathlib import Path
import sys


def _load_scripts():
    repo = Path(__file__).resolve().parents[1]
    scripts = repo / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))


def test_stvm_hello_world_flow():
    _load_scripts()
    from stasm import assemble_text  # type: ignore
    from stvm_core import STVM  # type: ignore

    source = """
start:
  CA.MOVI r0 2
  CA.MOVI r1 3
  CA.ADD r0 r1
  DR.ASSERT r0
  AV.SEND r0 1
  KO.HALT
"""
    program, _, _ = assemble_text(source)
    vm = STVM()
    vm.run(program, max_steps=100)

    assert vm.last_error is None
    assert vm.regs[0] == 5
    assert any("send ch=1 value=5" in e for e in vm.events)

