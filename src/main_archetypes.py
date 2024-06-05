# SPDX-FileCopyrightText: © 2022 Kevin Lu
# SPDX-Licence-Identifier: AGPL-3.0-or-later
from argparse import ArgumentParser
import logging
import os
import sys

from ruamel.yaml import YAML

from common import initial_parse, write


parser = ArgumentParser()
parser.add_argument("wikitext_directory", help="yaml-yugipedia archetypes and series")

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = parser.parse_args()
    yaml = YAML()
    yaml.width = sys.maxsize
    archetypes_list = []
    archetypes_map = {}
    for filename in os.listdir(args.wikitext_directory):
        filepath = os.path.join(args.wikitext_directory, filename)
        if os.path.isfile(filepath):
            logger.info(filepath)
            properties = initial_parse(yaml, filepath, "Infobox archseries")
            if not properties:
                logger.info(f"Skip: {filepath}")
                continue
            document = {
                "de": properties.get("de_name"),
                "es": properties.get("es_name"),
                "fr": properties.get("fr_name"),
                "it": properties.get("it_name"),
                "pt": properties.get("pt_name"),
                "ja": properties.get("ja_name"),
                "ja_romaji": properties.get("romaji"),
                "ko": properties.get("ko_name"),
                "ko_rr": properties.get("ko_romanized"),
                "zh-TW": properties.get("tc_name") or properties.get("zh_name"),
                "zh-CN": properties.get("sc_name"),
            }
            archetypes_map[properties.get("en_name")] = document
            archetypes_list.append({"en": properties.get("en_name"), **document})
    write(archetypes_map, "map", yaml, logger)
    write(archetypes_list, "list", yaml, logger)


if __name__ == "__main__":
    main()
