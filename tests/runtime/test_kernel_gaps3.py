"""Third gap-coverage pass for runtime/kernel.py."""

from __future__ import annotations

from pathlib import Path

from runtime.kernel import Kernel, KernelBuilder
from runtime.persona import PersonaDetector
from runtime.skill_resolver import SkillResolver


def _kernel(tmp_path: Path) -> Kernel:
    for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
        (tmp_path / sub).mkdir(parents=True, exist_ok=True)
    (tmp_path / "runtime/policies/default.yaml").write_text(
        "default_action: allow\nrules:\n"
        "  - name: deny-rm\n    condition: \"'rm -rf' in command\"\n    action: deny\n"
    )
    return Kernel(tmp_path)


class TestDenyMetric:
    def test_deny_increments_deny_label(self, tmp_path: Path) -> None:
        k = _kernel(tmp_path)
        result = k.act("exec", command="rm -rf /")
        assert result["ok"] is False


class TestMiddlewareHandler:
    def test_handler_executes_with_middleware(self, tmp_path: Path) -> None:
        k = _kernel(tmp_path)
        seen: list[str] = []

        def mw(ctx: object, nxt: object) -> object:
            seen.append("mw")
            return nxt()  # type: ignore[operator]

        k.use_middleware(mw)
        r = k.act("Read", dry_run=True)
        assert seen == ["mw"]
        assert r["ok"] is True


class TestBuilderKwargs:
    def test_build_no_root(self) -> None:
        k = KernelBuilder().build()
        assert isinstance(k, Kernel)

    def test_build_all_kwargs(self, tmp_path: Path) -> None:
        for sub in ("runtime/policies", "workflows", "rules", "tech-stack", "state", "brain"):
            (tmp_path / sub).mkdir(parents=True, exist_ok=True)
        sr = SkillResolver(root=tmp_path, project_root=tmp_path)
        pd = PersonaDetector()
        k = (
            KernelBuilder()
            .with_root(tmp_path)
            .with_project_root(tmp_path)
            .with_persona_detector(pd)
            .with_skill_resolver(sr)
            .build()
        )
        assert isinstance(k, Kernel)
