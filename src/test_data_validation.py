import json
import logging
import os
import sys
from typing import List, Tuple

from fastjsonschema import compile, JsonSchemaValueException


logger = logging.getLogger(__name__)


def validate_documents(schema_path: str, document_dir: str) -> None:
    with open(schema_path) as handle:
        validate = compile(json.load(handle))
    errors: List[Tuple[str, JsonSchemaValueException]] = []
    for root, dirs, files in os.walk(document_dir):
        for file in files:
            if file.endswith(".json"):
                path = os.path.join(root, file)
                with open(path) as handle:
                    document = json.load(handle)
                logger.info(path)
                try:
                    validate(document)
                except JsonSchemaValueException as e:
                    errors.append((file, e))
    for file, error in errors:
        logger.error(f"{file}: {error.message}")
    if len(errors):
        raise JsonSchemaValueException(f"{len(errors)} file(s) failed to validate")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    target = sys.argv[2] if len(sys.argv) > 2 else "."
    validate_documents(sys.argv[1], target)
