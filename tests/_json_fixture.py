"""JSON fixture boundaries for deliberately mutated validation inputs."""

from typing import Any, TypeAlias, cast

# Any is intentional: negative fixtures insert invalid nested shapes to test
# production validators. Production JSON types remain closed and unchanged.
JsonFixture: TypeAlias = dict[str, Any]


def json_fixture(value: object) -> JsonFixture:
    """Assert an object boundary before inspecting a dynamic fixture payload."""
    assert isinstance(value, dict)
    assert all(isinstance(key, str) for key in value)
    return cast(JsonFixture, value)
