from typing import Any


def value_of(value: str | None, default: str | None = None) -> str | None:
	if value is None:
		return default

	if isinstance(value, str) and value.strip() == '':
		return default

	if isinstance(value, list) and len(value) == 0:
		return default

	return value


# class name/index name is capitalized (user1 => User1) maybe because it is a class name,
# so the solution is to use Vector_user1 instead of user1
CLASS_NAME = lambda user_id: f"Vector_{user_id}"


def to_int(value: Any | None, default: int = 0) -> int:
	if value is None:
		return default

	try:
		return int(value)
	except ValueError:
		return default
