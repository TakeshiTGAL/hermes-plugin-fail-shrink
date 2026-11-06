"""Tool schema. The first sentence stays within 60 characters."""

FAIL_FULL = {
    "name": "fail_full",
    "description": (
        "Show one slice of a saved failure log. "
        "Pass the path and offset printed in the short block. "
        "The same call reads a saved pytest, jest, vitest, cargo, go test, tsc, ruff, or eslint log. "
        "This call does not write."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path printed on the full log line of the short block.",
            },
            "offset": {
                "type": "integer",
                "minimum": 0,
                "description": "Byte offset into that file. Default 0.",
            },
            "limit": {
                "type": "integer",
                "minimum": 1,
                "maximum": 32000,
                "description": "Maximum bytes to return. Default 8000. Maximum 32000.",
            },
        },
        "required": ["path"],
        "additionalProperties": False,
    },
}

ALL_SCHEMAS = [FAIL_FULL]
