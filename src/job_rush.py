# SPDX-FileCopyrightText: © 2022–2024 Kevin Lu
# SPDX-Licence-Identifier: AGPL-3.0-or-later
import json
import logging
import os
import sys
from multiprocessing import current_process
from typing import Any, Dict, List, Optional

from ruamel.yaml import YAML

from common import (
    int_or_og,
    initial_parse,
    int_or_none,
    replace_interlinear_annotations,
    transform_names,
    annotate_shared,
    transform_sets,
    transform_image,
    transform_multilanguage,
    write,
    load_ko_csv,
    str_or_none,
)

module_logger = logging.getLogger(__name__)


def transform_structure(wikitext: Dict[str, str]) -> Optional[Dict[str, Any]]:
    konami_id = int_or_none(wikitext.get("database_id"))
    document = {"konami_id": konami_id, "name": transform_names(wikitext)}
    if "condition" in wikitext:
        document["summoning_condition"] = transform_multilanguage(
            wikitext, "condition"
        )
    if "requirement" in wikitext:  # everything except Normal Monsters
        document["requirement"] = transform_multilanguage(wikitext, "requirement")
        if wikitext.get("effect_types"):
            document["effect_types"] = wikitext.get("effect_types", "").split(", ")
        document["effect"] = transform_multilanguage(wikitext, "text")
    else:
        document["text"] = transform_multilanguage(wikitext, "text")
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
    if "is_translation_unofficial" in wikitext:
        document["is_translation_unofficial"] = wikitext["is_translation_unofficial"]
    document["yugipedia_page_id"] = wikitext["yugipedia_page_id"]
    return document


def overwrite_field(
    logger: logging.Logger,
    document: Dict[str, Any],
    source: Dict[str, str],
    key: str,
    key_source: Optional[str] = None,
) -> None:
    if key_source is None:
        key_source = key
    if source[key_source]:
        if key in document:
            if key == "name":
                value = replace_interlinear_annotations(source[key_source])
            else:
                value = str_or_none(source[key_source])
            document[key]["ko"] = value
        else:
            logger.warn(f"Extraneous value for {key_source}")


def overwrite(
    logger: logging.Logger, document: Dict[str, Any], source: Dict[str, str]
) -> None:
    overwrite_field(logger, document, source, "text", "non_effect_monster_text")
    for key in ["name", "summoning_condition", "materials", "requirement", "effect"]:
        overwrite_field(logger, document, source, key)


def merge_ko(
    logger: logging.Logger,
    document: Dict[str, Any],
    ko_override: Optional[Dict[int, Dict[str, str]]],
    ko_prerelease: Optional[Dict[int, Dict[str, str]]],
) -> None:
    override = ko_override.get(document["konami_id"]) if ko_override else None
    prerelease = (
        ko_prerelease.get(document["yugipedia_page_id"]) if ko_prerelease else None
    )
    if override:
        sublogger = logger.getChild("override")
        sublogger.info(f"[{document['name']['ko']}] -> [{override['name']}]")
        overwrite(logger, document, override)
    if prerelease:
        sublogger = logger.getChild("prerelease")
        if document["name"]["ko"]:
            sublogger.warn(f"Extraneous row [{document['name']['ko']}]")
        else:
            sublogger.info(f"Injecting [{prerelease['name']}]")
            overwrite(logger, document, prerelease)
            flags = document.setdefault("is_translation_unofficial", {})
            flags.setdefault("name", {})["ko"] = True
            flags.setdefault("text", {})["ko"] = True


# On Yugipedia, Rush Duel cards inherit their Japanese name from their OCG counterpart
def annotate_ocg_ja_name(
    logger: logging.Logger, document: Dict[str, Any], ocg_cards: Dict[str, Any]
) -> None:
    name = document["name"]["en"]
    ocg_card = ocg_cards.get(name)
    if ocg_card and not document["name"]["ja"]:
        logger.info(f"Annotating [{name}] with Japanese OCG card name")
        document["name"]["ja"] = ocg_card["name"]["ja"]


def write_output(yaml: YAML, logger: logging.Logger, document: Dict[str, Any]) -> None:
    if document["konami_id"] is not None:
        basename = document["konami_id"]
    else:
        basename = f"yugipedia{document['yugipedia_page_id']}"
    write(document, basename, yaml, logger)


def job(
    wikitext_dir: str,
    filenames: List[str],
    ko_official_csv: Optional[str] = None,
    ko_override_csv: Optional[str] = None,
    ko_prerelease_csv: Optional[str] = None,
    ocg_aggregate: Optional[str] = None,
    return_results=False,
) -> Optional[List[Dict[str, Any]]]:
    yaml = YAML()
    yaml.width = sys.maxsize
    ko_official = load_ko_csv("konami_id", ko_official_csv)  # noqa: F841
    ko_override = load_ko_csv("konami_id", ko_override_csv)
    ko_prerelease = load_ko_csv("yugipedia_page_id", ko_prerelease_csv)
    if ocg_aggregate:
        with open(ocg_aggregate) as f:
            raw = json.load(f)
            ocg_cards = {card["name"]["en"]: card for card in raw}
    else:
        ocg_cards = None
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
            properties.get("level") == "???"
            or properties.get("attribute") == "???"
            or properties.get("atk") == "???"
            or properties.get("def") == "???"
            or properties.get("card_type") == "???"
            or properties.get("property") == "???"
            or
            # Not legal for play https://ygorganization.com/realspeedduel/
            properties.get("card_type") == "Skill"
        ):
            logger.info(f"Skip: {filepath}")
            continue
        properties["yugipedia_page_id"] = page_id
        document = transform_structure(properties)
        merge_ko(logger, document, ko_override, ko_prerelease)
        if ocg_cards:
            annotate_ocg_ja_name(logger, document, ocg_cards)
        write_output(yaml, logger, document)
        if return_results:
            results.append(document)
    if return_results:
        return results
