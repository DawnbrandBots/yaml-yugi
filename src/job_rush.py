# SPDX-FileCopyrightText: © 2022 Kevin Lu
# SPDX-Licence-Identifier: AGPL-3.0-or-later
import logging
import os
import sys
from multiprocessing import current_process
from typing import Any, Dict, List, Optional

from ruamel.yaml import YAML

from common import int_or_og, initial_parse, int_or_none, transform_names, transform_texts, annotate_shared, \
    transform_sets, transform_image, transform_multilanguage, write

module_logger = logging.getLogger(__name__)


def transform_structure(wikitext: Dict[str, str]) -> Optional[Dict[str, Any]]:
    konami_id = int_or_none(wikitext.get("database_id"))
    document = {
        "konami_id": konami_id,
        "name": transform_names(wikitext)
    }
    if "summoning_condition" in wikitext:
        document["summoning_condition"] = transform_multilanguage(wikitext, "summoning_condition")
    if "requirement" in wikitext:  # everything except Normal Monsters
        document["requirement"] = transform_multilanguage(wikitext, "requirement")
        if wikitext.get("effect_types"):
            document["effect_types"] = wikitext.get("effect_types", "").split(", ")
        document["effect"] = transform_texts(wikitext)
    else:
        document["text"] = transform_texts(wikitext)
    annotate_shared(document, wikitext)
    if "materials" in wikitext:  # Overwrite OCG/TCG "bonus field" for Fusion Monsters
        document["materials"] = transform_multilanguage(wikitext, "materials")
    if wikitext.get("maximum_atk"):
        document["maximum_atk"] = int_or_og(wikitext["maximum_atk"])
    if "Legend Card" in wikitext.get("misc", ""):
        document["legend"] = True
    if wikitext.get("image"):
        document["images"] = transform_image(wikitext.get("image"))
    document["sets"] = transform_sets(wikitext)
    document["yugipedia_page_id"] = wikitext["yugipedia_page_id"]
    return document


def write_output(yaml: YAML, logger: logging.Logger, document: Dict[str, Any]) -> None:
    if document["konami_id"] is not None:
        basename = document['konami_id']
    else:
        basename = f"yugipedia{document['yugipedia_page_id']}"
    write(document, basename, yaml, logger)


def job(
    wikitext_dir: str,
    filenames: List[str],
    return_results=False
) -> Optional[List[Dict[str, Any]]]:
    yaml = YAML()
    yaml.width = sys.maxsize
    results = []
    for i, filename in enumerate(filenames):
        filepath = os.path.join(wikitext_dir, filename)
        # This should always be int, but code defensively and allow future changes to yaml-yugipedia's structure
        basename = os.path.splitext(filename)[0]
        page_id = int_or_og(basename)
        logger = module_logger.getChild(current_process().name).getChild(basename)
        logger.info(f"{i}/{len(filenames)} {filepath}")

        properties = initial_parse(yaml, filepath)
        if not properties or (
            # Details unavailable for a new leak
            properties.get("level") == "???" or
            properties.get("attribute") == "???" or
            properties.get("atk") == "???" or
            properties.get("def") == "???"
        ):
            logger.info(f"Skip: {filepath}")
            continue
        properties["yugipedia_page_id"] = page_id
        document = transform_structure(properties)
        write_output(yaml, logger, document)
        if return_results:
            results.append(document)
    if return_results:
        return results
