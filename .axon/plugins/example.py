"""Example AXON plugin — copy and edit for your own commands."""


def register() -> dict:
    """Return slash command names (without /) mapped to handlers."""

    def hello(*args: str) -> str:
        """Say hello from a plugin."""
        name = " ".join(args).strip() or "world"
        return f"Hello, {name}! (from example plugin)"

    return {"hello": hello}
