"""Shrink a classified test failure and keep the full log on disk."""

from pathlib import Path

from . import hooks, schemas, tools

_SKILL = Path(__file__).resolve().parent / "skills" / "read-a-failure" / "SKILL.md"
_SKILL_TEXT = (
    "Read a saved test failure when the short block is not enough. "
    "Call fail_full with the path and offset from that block."
)


def register(ctx) -> None:
    for schema in schemas.ALL_SCHEMAS:
        ctx.register_tool(
            name=schema["name"],
            toolset="fail-shrink",
            schema=schema,
            handler=tools.handle_fail_full,
            description=schema["description"],
        )
    ctx.register_skill("read-a-failure", _SKILL, description=_SKILL_TEXT)

    def _pre_llm_call(**kwargs):
        return hooks.on_pre_llm_call(**kwargs)

    def _transform(**kwargs):
        return hooks.on_transform(ctx, **kwargs)

    ctx.register_hook("pre_llm_call", _pre_llm_call)
    ctx.register_hook("transform_tool_result", _transform)
