from typing import Any
from typing import TypeVar

from pydantic import BaseModel
from pydantic import TypeAdapter
from pydantic import ValidationError

from orbyte.error_handling.error_codes import OrbyteErrorCode
from orbyte.error_handling.exceptions import OrbyteError

T = TypeVar("T")


def shallow_model_dump(model_instance: BaseModel) -> dict[str, Any]:
    """Like model_dump(), but returns references to field values instead of
    deep copies. Use with model_construct() to avoid unnecessary memory
    duplication when building subclass instances."""
    return {
        field_name: getattr(model_instance, field_name)
        for field_name in model_instance.__class__.model_fields
    }


def parse_json_form_field(raw: str, adapter: TypeAdapter[T], field_name: str) -> T:
    """Parse a JSON-encoded multipart form field, validating against ``adapter``.
    Raises ``OrbyteError(INVALID_INPUT)`` naming the field on bad JSON or wrong
    shape instead of leaking a pydantic ``ValidationError``."""
    try:
        return adapter.validate_json(raw)
    except ValidationError as e:
        raise OrbyteError(
            OrbyteErrorCode.INVALID_INPUT,
            f"{field_name} is not valid JSON of the expected shape.",
        ) from e
