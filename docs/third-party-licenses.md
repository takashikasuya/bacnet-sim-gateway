# Third-party licenses

`bbc-sim` is distributed under **Apache-2.0**. All dependencies use permissive
licenses compatible with Apache-2.0 redistribution. **No copyleft (GPL / LGPL /
AGPL) dependencies** are present.

## Runtime dependencies

| Package | License | Apache-2.0 compatible |
|---------|---------|:---:|
| bacpypes3 | MIT | ✅ |
| pyyaml | MIT | ✅ |
| typer | MIT | ✅ |
| paho-mqtt | EPL-2.0 OR BSD-3-Clause | ✅ (BSD option) |
| pyzmq | BSD-3-Clause | ✅ |
| fastapi | MIT | ✅ |
| uvicorn | BSD-3-Clause | ✅ |
| jinja2 | BSD-3-Clause | ✅ |
| pydantic / pydantic-core | MIT | ✅ |
| starlette | BSD-3-Clause | ✅ |
| click | BSD-3-Clause | ✅ |
| anyio, h11, rich, markdown-it-py, mdurl, typing-extensions, … (transitive) | MIT / BSD / PSF | ✅ |
| certifi (transitive) | MPL-2.0 | ✅ (file-level copyleft, compatible) |

## Optional extras

| Extra | Package | License |
|-------|---------|---------|
| `amqp` | python-qpid-proton | Apache-2.0 |
| `grpc` | grpcio, grpcio-tools | Apache-2.0 |
| `grpc` | protobuf | BSD-3-Clause |

## Notes

- `paho-mqtt` is dual-licensed (EPL-2.0 **or** BSD-3-Clause); we rely on the
  BSD-3-Clause option, which is Apache-2.0 compatible.
- `MPL-2.0` packages (e.g. `certifi`, `pathspec`) are weak/file-level copyleft and
  compatible with Apache-2.0 distribution; they are transitive dependencies.
- Dev-only tools (pytest, ruff, mypy, coverage, playwright, …) are MIT/BSD/Apache
  and are not redistributed with the package.

## Regenerate

```bash
uv sync
uvx --from pip-licenses pip-licenses --python "$(pwd)/.venv/bin/python" \
  --format=markdown --order=license
```
