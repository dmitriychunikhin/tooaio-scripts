from collections.abc import Iterable
from typing import Any, get_args, get_origin, Literal
from typing_extensions import TypeIs
from typing import TextIO
from enum import StrEnum, Enum
import re
import pydantic
import pydantic_settings
from pydantic_core import PydanticSerializationError


def _str_simple(value: Any, indent: int = 4, outer_quotes: str = "'") -> str:  # noqa ANN401
    if not outer_quotes:
        outer_quotes = "'"

    if value is None:
        return ""

    if isinstance(value, type):
        return ""

    if isinstance(value, str):
        strval = value.strip()
        if not outer_quotes:
            strval = f'"{strval}"' if "'" in strval else f"'{strval}'"
        else:
            strval_stripq = strval.strip(outer_quotes)
            strval = (
                outer_quotes + re.sub(r"([^\\])" + outer_quotes, r"\1\\" + outer_quotes, strval_stripq) + outer_quotes
            )

        return strval

    try:
        adapter = pydantic.TypeAdapter(Any, config=pydantic.ConfigDict(arbitrary_types_allowed=True))
        return adapter.dump_json(value, indent=indent).decode()
    except PydanticSerializationError:
        return ""


def _str_simple_list(items: Iterable[Any], outer_qoutes: str = "'") -> list[str]:
    return [item for item in [_str_simple(item, outer_quotes=outer_qoutes) for item in items] if item]


def _is_enum(value: type) -> TypeIs[type[Enum]]:
    return issubclass(value, (Enum, StrEnum))


def _is_literal(value: object) -> bool:
    return get_origin(value) is Literal


def _str_list_enumerated_type(value: Any) -> list[str]:  # noqa ANN401
    if _is_enum(value):
        return _str_simple_list([item.value for item in value.__members__.values()])
    elif _is_literal(value):
        return _str_simple_list(get_args(value))
    else:
        return []


def build_env_example(
    model: type[pydantic_settings.BaseSettings | pydantic.BaseModel], file: TextIO | None = None
) -> None:
    output_line_length = 80

    if model.__doc__:
        print(f"""# {"\n# ".join(model.__doc__.strip().splitlines())}""", file=file)
        print("", file=file)

    fields_required: list[str] = []
    fields_notrequired: list[str] = []
    for field_name, field_info in model.model_fields.items():
        field_description = field_info.description
        if field_description:
            print(f"# {'\n# '.join(field_description.strip().splitlines())}", file=file)

        field_annotation = field_info.annotation
        if field_annotation:
            vals = _str_list_enumerated_type(field_annotation)
            if vals:
                print("# Возможные значения: ", file=file)
                vals_str = f"# {', '.join(vals)}"
                if len(vals_str) > output_line_length:
                    vals_str = f"# {'\n# '.join(vals)}"
                print(vals_str, file=file)

        field_value = _str_simple(field_info.default)

        example_values = []
        for example_value in field_info.examples or []:
            example_value = _str_simple(example_value)
            if not example_value:
                continue
            if not field_value:
                field_value = example_value
            example_values.append(example_value)
        if len(example_values) == 1:
            example_values.remove(field_value)

        if example_values:
            print("# Примеры значений", file=file)
            for example_value in example_values:
                print(f"# {example_value}", file=file)

        print(f"{field_name} = {field_value}", file=file)

        if field_info.is_required():
            fields_required.append(field_name)
        else:
            fields_notrequired.append(field_name)

        print("", file=file)

    if not fields_required:
        print("# Обязательные параметры отсутствуют", file=file)
    else:
        print("# Обязательные параметры: ", file=file)
        for field_name in fields_required:
            print(f"# {field_name}", file=file)
    print("", file=file)

    if not fields_notrequired:
        print("# Необязательные параметры отсутствуют", file=file)
    else:
        print("# Необязательные параметры: ", file=file)
        for field_name in fields_notrequired:
            print(f"# {field_name}", file=file)
    print("", file=file)


class JSONSchemaNodeType(StrEnum):
    ROOT = "root"
    REF = "ref"
    TYPE_UNION = "anyOf"
    ARRAY = "array"
    OBJECT = "object_body"
    OBJECT_PROPERTY = "object_property"
    ARRAY_VALUE = "array_value"


def build_json_example(
    model: type[pydantic_settings.BaseSettings | pydantic.BaseModel], file: TextIO | None = None
) -> None:
    schema_dict = model.model_json_schema()
    defs = schema_dict.pop("$defs", {})

    print("// Описание схемы в формате JSON5, при копировании в JSON удалите комметарии", file=file)
    print("", file=file)

    def schema_to_json5(
        schema: dict[str, Any] | list[Any], indent_level: int, node_type: JSONSchemaNodeType
    ) -> tuple[str, str]:
        spacing = "  " * indent_level
        spacing_commets = "  " * max(indent_level, 0)
        lines_before = []
        lines_after = []

        if isinstance(schema, dict):
            if "$ref" in schema:
                ref_name = schema["$ref"].split("/")[-1]
                ref_dict = defs[ref_name]
                parent_has_description = False
                if node_type == JSONSchemaNodeType.ARRAY:
                    parent_has_description = True
                elif "description" in schema:
                    desc_lines = (schema["description"] or "").strip().splitlines()
                    parent_has_description = bool(desc_lines)
                    for desc_line in desc_lines:
                        lines_before.append(f"{spacing_commets}// {desc_line}")

                save_ref_description = ""
                if parent_has_description and "description" in ref_dict:
                    save_ref_description = ref_dict.pop("description", "")

                str_before, str_after = schema_to_json5(ref_dict, indent_level, JSONSchemaNodeType.REF)

                if save_ref_description:
                    ref_dict["description"] = save_ref_description

                if str_before:
                    lines_before.append(f"{str_before}")
                if str_after:
                    lines_after.append(f"{str_after}")
                return "\n".join(lines_before), "\n".join(lines_after)

            is_type = "type" in schema
            type_name = schema["type"] if is_type else ""
            is_object = type_name == "object"
            is_array = type_name == "array"

            if is_object:
                lines_after.append(spacing + "{")

            if "description" in schema:
                desc_lines = (schema["description"] or "").strip().splitlines()
                for desc_line in desc_lines:
                    lines_before.append(f"{spacing_commets}// {desc_line}")

            if is_type and "enum" in schema and isinstance(schema["enum"], list):
                enum_values = schema["enum"]
                lines_before.append(
                    f"{spacing}// Возможные значения: " + ", ".join(_str_simple_list(enum_values, outer_qoutes='"'))
                )
                return "\n".join(lines_before), "\n".join(lines_after)

            is_type_union = "anyOf" in schema and isinstance(schema["anyOf"], list)
            if is_type_union:
                type_list = schema["anyOf"]
                type_list_null_val = {"type": "null"}
                type_list_has_null = False
                if type_list_null_val in type_list:
                    type_list_has_null = True
                    type_list.pop(type_list.index(type_list_null_val))

                if type_list_has_null:
                    lines_before.append(f"{spacing}// Необязательное")
                if len(type_list) > 1:
                    lines_after.append(f"{spacing}// Возможные значения")
                else:
                    type_list = type_list[0]

                str_before, str_after = schema_to_json5(type_list, indent_level, JSONSchemaNodeType.TYPE_UNION)

                if type_list_has_null:
                    type_list = schema["anyOf"]
                    type_list.append(type_list_null_val)

                if str_before:
                    lines_after.append(f"{str_before}")
                if str_after:
                    lines_after.append(f"{str_after}")
                return "\n".join(lines_before), "\n".join(lines_after)

            if is_array and "items" in schema:
                str_before, str_after = schema_to_json5(schema["items"], indent_level + 1, JSONSchemaNodeType.ARRAY)

                lines_after.append(f"{spacing}[")
                if str_before:
                    lines_after.append(f"{str_before}")
                if str_after:
                    lines_after.append(f"{str_after},")
                lines_after.append(f"{spacing}]")
                return "\n".join(lines_before), "\n".join(lines_after)

            if not is_type and node_type != JSONSchemaNodeType.OBJECT:
                return "", ""

            items = list(schema.items())

            for i, (key, value) in enumerate(items):
                if isinstance(value, dict):
                    if is_object and key == "properties":
                        str_before, str_after = schema_to_json5(value, indent_level + 1, JSONSchemaNodeType.OBJECT)
                        if str_before:
                            lines_after.append(str_before)
                        if str_after:
                            lines_after.append(str_after)

                    elif node_type == JSONSchemaNodeType.OBJECT:
                        str_before, str_after = schema_to_json5(value, indent_level, JSONSchemaNodeType.OBJECT_PROPERTY)
                        if str_before:
                            lines_after.append(str_before)

                        property_type_name = value.get("type", "")

                        # if "type" in value:
                        #     lines_after.append(f"{spacing_commets}// тип: {_str_simple(value["type"])}")

                        default_str = ""
                        if "default" in value:
                            default_val = value["default"]
                            default_str = _str_simple(default_val, outer_quotes='"')

                            if default_str and isinstance(default_val, (str, int, bool)):
                                default_str = spacing + f"\n{spacing}".join(default_str.splitlines())
                            else:
                                default_str = ""

                        if not default_str:
                            if property_type_name == "boolean":
                                default_str = "false"
                            elif property_type_name in ("integer", "number"):
                                default_str = "0"
                            elif property_type_name == "string":
                                default_str = '""'
                            elif property_type_name == "array":
                                default_str = "[]"
                            elif not property_type_name:
                                default_str = ""
                            else:
                                default_str = "null"

                        if property_type_name == "array" and "items" in value and "$ref" in value["items"]:
                            default_str = ""

                        if default_str:
                            # default_str = default_str.strip("'")
                            str_after = f"{default_str}\n" + str_after

                        lines_after.append(f'{spacing}"{key}": {str_after.strip()}')

                        if i < len(items) - 1 and lines_after:
                            lines_after[-1] += ","

                elif is_type and not is_object and type_name == "null":
                    lines_after.append(f"{spacing}{type_name}")
                    return "\n".join(lines_before), "\n".join(lines_after)

            if is_object:
                lines_after.append(spacing + "}")

            return "\n".join(lines_before), "\n".join(lines_after)

        elif isinstance(schema, list):
            lines_after.append(f"{spacing}[")
            for i, item in enumerate(schema):
                str_before, str_after = schema_to_json5(item, indent_level + 1, JSONSchemaNodeType.ARRAY_VALUE)
                if str_before:
                    lines_after.append(f"{str_before}")
                if str_after:
                    lines_after.append(f"{str_after}")
                if i < len(schema) - 1 and lines_after:
                    lines_after[-1] += ","
            lines_after.append(f"{spacing}]")
            return "\n".join(lines_before), "\n".join(lines_after)

        else:
            return "", _str_simple(schema, outer_quotes='"')

    str_before, str_after = schema_to_json5(schema_dict, 0, JSONSchemaNodeType.ROOT)
    print(str_before, file=file)
    print(str_after, file=file)
