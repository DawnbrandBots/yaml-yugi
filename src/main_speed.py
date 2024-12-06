# SPDX-FileCopyrightText: © 2022 Kevin Lu
# SPDX-Licence-Identifier: AGPL-3.0-or-later
from argparse import ArgumentParser
import json
import logging
import os
import sys
from typing import Dict, Any, Optional

from ruamel.yaml import YAML

from common import (
    int_or_og,
    initial_parse,
    transform_names,
    transform_multilanguage,
    transform_sets,
    write,
)

parser = ArgumentParser()
parser.add_argument("wikitext_directory", help="yaml-yugipedia card texts")
parser.add_argument(
    "--generate-schema", action="store_true", help="output generated JSON schema file"
)
parser.add_argument("--aggregate", help="output aggregate JSON file")

logger = logging.getLogger(__name__)


def transform_structure(wikitext: Dict[str, str]) -> Optional[Dict[str, Any]]:
    return {
        "name": transform_names(wikitext),
        "type_line": wikitext["types"],
        "activation": transform_multilanguage(wikitext, "skill_activation"),
        "effect": transform_multilanguage(wikitext, "text"),
        "character": wikitext.get("character"),  # bonus field
        "image_front": wikitext.get("image"),
        "image_back": wikitext.get("image2"),
        "sets": transform_sets(wikitext),
        "yugipedia_page_id": wikitext.get("yugipedia_page_id"),
    }


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = parser.parse_args()
    yaml = YAML()
    yaml.width = sys.maxsize
    skills = []
    for filename in os.listdir(args.wikitext_directory):
        filepath = os.path.join(args.wikitext_directory, filename)
        if os.path.isfile(filepath):
            logger.info(filepath)
            basename = os.path.splitext(filename)[0]
            page_id = int_or_og(basename)
            properties = initial_parse(yaml, filepath)
            if not properties:
                logger.info(f"Skip: {filepath}")
                continue
            properties["yugipedia_page_id"] = page_id
            skill = transform_structure(properties)
            write(skill, f"yugipedia{page_id}", yaml, logger)
            if args.aggregate is not None:
                skills.append(skill)

    if args.aggregate is not None:
        logger.info(f"Write: {args.aggregate}")
        with open(args.aggregate, "w", encoding="utf-8") as out:
            json.dump(skills, out)


if __name__ == "__main__":
    main()
