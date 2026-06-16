# AXON plugins

Drop Python files here. Each plugin exposes `register()` returning command handlers.

## Example (`hello.py`)

```python
def register():
    def hello(*args):
        return "Hello from plugin!"

    hello.__doc__ = "Say hello"
    return {"hello": hello}
```

Reload AXON after adding plugins. Future versions will expose `/hello` in the REPL automatically.
