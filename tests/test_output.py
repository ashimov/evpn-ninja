"""Tests for output formatters."""

import json
from dataclasses import dataclass
from enum import Enum
from io import StringIO
from unittest.mock import patch

import pytest
import yaml
from rich.console import Console

from evpn_ninja.output import (
    OutputFormat,
    _serialize,
    configure_console,
    console,
    output_config,
    output_json,
    output_key_value,
    output_table,
    output_yaml,
    print_error,
    print_info,
    print_success,
    print_warning,
)


class TestOutputFormatters:
    """Test cases for output formatters."""

    def test_output_format_enum(self):
        """Test OutputFormat enum values."""
        assert OutputFormat.JSON.value == "json"
        assert OutputFormat.YAML.value == "yaml"
        assert OutputFormat.TABLE.value == "table"

    def test_serialize_dict(self):
        """Test serialization of dict."""
        data = {"name": "test", "value": 42}
        result = _serialize(data)

        assert result == data

    def test_serialize_list(self):
        """Test serialization of list."""
        data = [{"id": 1}, {"id": 2}]
        result = _serialize(data)

        assert result == data

    def test_serialize_nested(self):
        """Test serialization of nested structure."""
        data = {
            "level1": {
                "level2": {
                    "level3": "deep value"
                }
            }
        }
        result = _serialize(data)

        assert result["level1"]["level2"]["level3"] == "deep value"

    def test_serialize_empty(self):
        """Test serialization of empty data."""
        result = _serialize({})
        assert result == {}

        result = _serialize([])
        assert result == []

    def test_serialize_special_characters(self):
        """Test serialization handles special characters."""
        data = {"message": "Hello \"World\"", "path": "C:\\Users"}
        result = _serialize(data)

        assert result["message"] == "Hello \"World\""
        assert result["path"] == "C:\\Users"


class TestJSONSerialization:
    """Test cases for JSON serialization."""

    def test_json_serialization(self):
        """Test JSON output produces valid JSON."""
        data = {"name": "Test", "value": 42}
        serialized = _serialize(data)
        json_str = json.dumps(serialized, indent=2)
        parsed = json.loads(json_str)

        assert parsed == data

    def test_json_nested_structure(self):
        """Test JSON handles nested structures."""
        data = {"outer": {"inner": {"deep": [1, 2, 3]}}}
        serialized = _serialize(data)
        json_str = json.dumps(serialized)
        parsed = json.loads(json_str)

        assert parsed["outer"]["inner"]["deep"] == [1, 2, 3]

    def test_json_unicode(self):
        """Test JSON handles unicode characters."""
        data = {"message": "Привет мир", "emoji": "Hello"}
        serialized = _serialize(data)
        json_str = json.dumps(serialized, ensure_ascii=False)
        parsed = json.loads(json_str)

        assert parsed["message"] == "Привет мир"


class TestYAMLSerialization:
    """Test cases for YAML serialization."""

    def test_yaml_serialization(self):
        """Test YAML output produces valid YAML."""
        data = {"name": "Test", "value": 42}
        serialized = _serialize(data)
        yaml_str = yaml.dump(serialized)
        parsed = yaml.safe_load(yaml_str)

        assert parsed == data

    def test_yaml_list_handling(self):
        """Test YAML handles lists correctly."""
        data = {"items": ["a", "b", "c"]}
        serialized = _serialize(data)
        yaml_str = yaml.dump(serialized)
        parsed = yaml.safe_load(yaml_str)

        assert parsed["items"] == ["a", "b", "c"]

    def test_yaml_nested_structure(self):
        """Test YAML preserves nested structure."""
        data = {
            "level1": {
                "level2": {
                    "level3": "deep value"
                }
            }
        }
        serialized = _serialize(data)
        yaml_str = yaml.dump(serialized)
        parsed = yaml.safe_load(yaml_str)

        assert parsed["level1"]["level2"]["level3"] == "deep value"


class TestSerializeDataclasses:
    """Test serialization of dataclasses."""

    def test_serialize_simple_dataclass(self) -> None:
        """Test serialization of simple dataclass."""
        @dataclass
        class SimpleData:
            name: str
            value: int

        obj = SimpleData(name="test", value=42)
        result = _serialize(obj)

        assert result == {"name": "test", "value": 42}

    def test_serialize_nested_dataclass(self) -> None:
        """Test serialization of nested dataclass."""
        @dataclass
        class Inner:
            x: int

        @dataclass
        class Outer:
            inner: Inner
            name: str

        obj = Outer(inner=Inner(x=10), name="outer")
        result = _serialize(obj)

        assert result == {"inner": {"x": 10}, "name": "outer"}

    def test_serialize_dataclass_with_list(self) -> None:
        """Test serialization of dataclass containing list."""
        @dataclass
        class WithList:
            items: list[str]

        obj = WithList(items=["a", "b", "c"])
        result = _serialize(obj)

        assert result == {"items": ["a", "b", "c"]}


class TestSerializeEnums:
    """Test serialization of enums."""

    def test_serialize_string_enum(self) -> None:
        """Test serialization of string enum."""
        class Color(str, Enum):
            RED = "red"
            BLUE = "blue"

        result = _serialize(Color.RED)
        assert result == "red"

    def test_serialize_int_enum(self) -> None:
        """Test serialization of int enum."""
        class Priority(Enum):
            LOW = 1
            HIGH = 10

        result = _serialize(Priority.HIGH)
        assert result == 10

    def test_serialize_dict_with_enum_values(self) -> None:
        """Test serialization of dict containing enum values."""
        class Status(str, Enum):
            ACTIVE = "active"
            INACTIVE = "inactive"

        data = {"status": Status.ACTIVE, "count": 5}
        result = _serialize(data)

        assert result == {"status": "active", "count": 5}


class TestConfigureConsole:
    """Test configure_console function."""

    def test_configure_console_no_color(self) -> None:
        """Test configuring console with no color."""
        import evpn_ninja.output as output_module

        original_console = output_module.console
        try:
            configure_console(no_color=True)
            assert output_module.console.no_color is True
        finally:
            output_module.console = original_console

    def test_configure_console_with_color(self) -> None:
        """Test configuring console with color enabled."""
        import evpn_ninja.output as output_module

        original_console = output_module.console
        try:
            configure_console(no_color=False)
            assert output_module.console.no_color is False
        finally:
            output_module.console = original_console


class TestOutputFunctions:
    """Test output functions."""

    def test_output_json_simple(self) -> None:
        """Test JSON output with simple data."""
        output = StringIO()
        test_console = Console(file=output, force_terminal=False, no_color=True)

        with patch("evpn_ninja.output.console", test_console):
            output_json({"key": "value"})

        result = output.getvalue()
        parsed = json.loads(result)
        assert parsed == {"key": "value"}

    def test_output_json_with_indent(self) -> None:
        """Test JSON output respects indent parameter."""
        output = StringIO()
        test_console = Console(file=output, force_terminal=False, no_color=True)

        with patch("evpn_ninja.output.console", test_console):
            output_json({"key": "value"}, indent=4)

        result = output.getvalue()
        assert "    " in result  # 4-space indent

    def test_output_yaml_simple(self) -> None:
        """Test YAML output with simple data."""
        output = StringIO()
        test_console = Console(file=output, force_terminal=False, no_color=True)

        with patch("evpn_ninja.output.console", test_console):
            output_yaml({"key": "value"})

        result = output.getvalue()
        parsed = yaml.safe_load(result)
        assert parsed == {"key": "value"}

    def test_output_table(self) -> None:
        """Test table output."""
        output = StringIO()
        test_console = Console(file=output, force_terminal=False, no_color=True)

        with patch("evpn_ninja.output.console", test_console):
            output_table(
                title="Test Table",
                columns=["Col1", "Col2"],
                rows=[["a", "b"], ["c", "d"]],
            )

        result = output.getvalue()
        assert "Test Table" in result
        assert "Col1" in result
        assert "Col2" in result

    def test_output_table_with_caption(self) -> None:
        """Test table output with caption renders without error."""
        output = StringIO()
        test_console = Console(file=output, force_terminal=False, no_color=True, width=120)

        with patch("evpn_ninja.output.console", test_console):
            output_table(
                title="Test",
                columns=["A"],
                rows=[["1"]],
                caption="This is a test caption",
            )

        result = output.getvalue()
        # Caption is rendered but may be wrapped; just verify output exists
        assert len(result) > 0
        assert "Test" in result

    def test_output_key_value(self) -> None:
        """Test key-value output."""
        output = StringIO()
        test_console = Console(file=output, force_terminal=False, no_color=True)

        with patch("evpn_ninja.output.console", test_console):
            output_key_value("Test Panel", {"key1": "value1", "key2": "value2"})

        result = output.getvalue()
        assert "Test Panel" in result
        assert "key1" in result
        assert "value1" in result

    def test_output_config(self) -> None:
        """Test config output with syntax highlighting."""
        output = StringIO()
        test_console = Console(file=output, force_terminal=False, no_color=True)

        with patch("evpn_ninja.output.console", test_console):
            output_config("Config Title", "hostname switch01", language="text")

        result = output.getvalue()
        assert "Config Title" in result
        assert "hostname switch01" in result


class TestPrintFunctions:
    """Test print helper functions."""

    def test_print_success(self) -> None:
        """Test print_success function."""
        output = StringIO()
        test_console = Console(file=output, force_terminal=False, no_color=True)

        with patch("evpn_ninja.output.console", test_console):
            print_success("Operation completed")

        result = output.getvalue()
        assert "Operation completed" in result

    def test_print_error(self) -> None:
        """Test print_error function."""
        output = StringIO()
        test_console = Console(file=output, force_terminal=False, no_color=True)

        with patch("evpn_ninja.output.console", test_console):
            print_error("Something went wrong")

        result = output.getvalue()
        assert "Error" in result
        assert "Something went wrong" in result

    def test_print_warning(self) -> None:
        """Test print_warning function."""
        output = StringIO()
        test_console = Console(file=output, force_terminal=False, no_color=True)

        with patch("evpn_ninja.output.console", test_console):
            print_warning("This is a warning")

        result = output.getvalue()
        assert "Warning" in result
        assert "This is a warning" in result

    def test_print_info(self) -> None:
        """Test print_info function."""
        output = StringIO()
        test_console = Console(file=output, force_terminal=False, no_color=True)

        with patch("evpn_ninja.output.console", test_console):
            print_info("Information message")

        result = output.getvalue()
        assert "Info" in result
        assert "Information message" in result
