# SPDX-FileCopyrightText: © 2022 Kevin Lu
# SPDX-Licence-Identifier: AGPL-3.0-or-later
import csv
import json
import logging
from multiprocessing import current_process
import os
import sys
from typing import Any, Dict, List, NamedTuple, Optional, Union

from ruamel.yaml import YAML

from common import initial_parse, int_or_none, int_or_og, transform_sets, transform_names, transform_texts, transform_image, annotate_shared

module_logger = logging.getLogger(__name__)


def annotate_zh_cn(yaml: YAML, logger: logging.Logger, zh_cn_dir: str, wikitext: Dict[str, str]) -> None:
    password = int_or_none(wikitext.get("password") or "")
    zh_cn_path = os.path.join(zh_cn_dir, f"{password}.yaml")
    if os.path.isfile(zh_cn_path):
        logger.info(f"zh-CN: {zh_cn_path}")
        with open(zh_cn_path) as f:
            document = yaml.load(f)
            wikitext["ourocg_name"] = document["name"]
            wikitext["ourocg_text"] = document["text"]
            if document.get("pendulum"):
                wikitext["ourocg_pendulum"] = document["pendulum"]


def transform_structure(logger: logging.Logger, wikitext: Dict[str, str]) -> Optional[Dict[str, Any]]:
    if (
        # Normal monster version OCG prize cards, Tyler, OG Egyptian Gods
        wikitext.get("database_id") == "none" or
        # Match winners, Command Duel-Use Card (only one with dbid None), etc. have db ids but no passwords
        "limitation_text" in wikitext or
        # Boss Duel cards
        wikitext.get("ocg_status") == "Illegal"
    ):
        logger.info(f"Skip: {wikitext}")
        return
    konami_id = int_or_none(wikitext.get("database_id"))
    password = int_or_none(wikitext.get("password"))
    document = {
        "konami_id": konami_id,
        "password": password,
        "name": transform_names(wikitext, wikitext.get("ourocg_name")),
        "text": transform_texts(wikitext, wikitext.get("ourocg_text"))
    }
    annotate_shared(document, wikitext)
    if wikitext.get("image"):
        document["images"] = transform_image(wikitext.get("image"))
    document["sets"] = transform_sets(wikitext)
    document["limit_regulation"] = {
        "tcg": wikitext.get("tcg_status"),
        "ocg": wikitext.get("ocg_status")
    }
    if "tcg_speed_duel_status" in wikitext:
        document["limit_regulation"]["speed"] = wikitext["tcg_speed_duel_status"]
    document["yugipedia_page_id"] = wikitext["yugipedia_page_id"]
    return document


LIMIT_REGULATION_MAPPING = {
    0: "Forbidden",
    1: "Limited",
    2: "Semi-Limited",
    None: "Unlimited"
}


def annotate_limit_regulation(document: Dict[str, Any],
                              tcg_vector: Optional[Dict[str, int]],
                              ocg_vector: Optional[Dict[str, int]]) -> None:
    if tcg_vector and document["konami_id"] and document["limit_regulation"]["tcg"] is None and "en" in document["sets"]:
        document["limit_regulation"]["tcg"] = LIMIT_REGULATION_MAPPING[tcg_vector.get(str(document["konami_id"]))]
    if ocg_vector and document["name"]["en"] and document["limit_regulation"]["ocg"] is None and "ja" in document["sets"]:
        document["limit_regulation"]["ocg"] = LIMIT_REGULATION_MAPPING[ocg_vector.get(document["name"]["en"])]


def write_output(yaml: YAML, logger: logging.Logger, document: Dict[str, Any]) -> None:
    if document["password"] is not None:
        # Recreate eight-digit password with left-padded 0s
        basename = str(document["password"]).rjust(8, "0")
    elif document["konami_id"] is not None:
        basename = f"kdb{document['konami_id']}"
    else:
        basename = f"yugipedia{document['yugipedia_page_id']}"
    logger.info(f"Write: {basename}.yaml")
    with open(f"{basename}.yaml", mode="w", encoding="utf-8") as out:
        yaml.dump(document, out)
    logger.info(f"Write: {basename}.json")
    with open(f"{basename}.json", mode="w", encoding="utf-8") as out:
        json.dump(document, out)


class Assignments(NamedTuple):
    # values: fake_password
    yugipedia: Dict[int, Union[int, List[int]]]
    # values: fake_password_range
    set_abbreviation: Dict[str, Union[int, List[int]]]


def load_assignments(yaml: YAML, file: str) -> Assignments:
    with open(file) as f:
        document = yaml.load(f)
    assignments = Assignments({}, {})
    for item in document:
        if "yugipedia" in item:
            assignments.yugipedia[item["yugipedia"]] = item["fake_password"]
        elif "set_abbreviation" in item:
            assignments.set_abbreviation[item["set_abbreviation"]] = item["fake_password_range"]
    return assignments


def annotate_assignments(document: Dict[str, Any], assignments: Assignments) -> None:
    # Direct assignment, may be used for certain passwordless cards or individual prereleases
    page_id = document["yugipedia_page_id"]
    if page_id in assignments.yugipedia:
        document["fake_password"] = assignments.yugipedia[page_id]
        return

    # Prerelease password assignment by set
    if document["password"] is None:
        if "ja" in document["sets"] and len(document["sets"]["ja"]) == 1:
            release = document["sets"]["ja"][0]
        elif "en" in document["sets"] and len(document["sets"]["en"]) == 1:
            release = document["sets"]["en"][0]
        else:
            return
        # https://yugipedia.com/wiki/Card_Number
        # one-character region codes and two-digit position numbers are no longer a thing
        set_abbreviation, position = release["set_number"].split("-")
        if set_abbreviation in assignments.set_abbreviation:
            position = int(position[2:])
            if isinstance(assignments.set_abbreviation[set_abbreviation], int):
                document["fake_password"] = position + assignments.set_abbreviation[set_abbreviation]
            else:  # list
                document["fake_password"] = [
                    position + fake_range for fake_range in
                    assignments.set_abbreviation[set_abbreviation]
                ]


def load_ko(ko_file: str) -> Dict[int, str]:
    with open(ko_file, encoding="utf8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        return {
            int(row["kid"]): row["name"]
            for row in reader
        }


def override_ko(document: Dict[str, Any], ko_overrides: Dict[int, str]) -> None:
    if document["konami_id"] and ko_overrides.get(document["konami_id"]):
        document["name"]["ko"] = ko_overrides.get(document["konami_id"])


def job(
    wikitext_dir: str,
    filenames: List[str],
    zh_cn_dir: Optional[str],
    assignment_file: Optional[str],
    tcg_vector: Optional[Dict[str, int]],
    ocg_vector: Optional[Dict[str, int]],
    ko_file: Optional[str],
    return_results=False
) -> Optional[List[Dict[str, Any]]]:
    yaml = YAML()
    yaml.width = sys.maxsize
    assignments = load_assignments(yaml, assignment_file) if assignment_file else None
    ko_overrides = load_ko(ko_file) if ko_file else None
    results = []
    for i, filename in enumerate(filenames):
        filepath = os.path.join(wikitext_dir, filename)
        # This should always be int, but code defensively and allow future changes to yaml-yugipedia's structure
        basename = os.path.splitext(filename)[0]
        page_id = int_or_og(basename)
        logger = module_logger.getChild(current_process().name).getChild(basename)
        logger.info(f"{i}/{len(filenames)} {filepath}")

        properties = initial_parse(yaml, filepath)
        properties["yugipedia_page_id"] = page_id
        if zh_cn_dir:
            annotate_zh_cn(yaml, logger, zh_cn_dir, properties)
        document = transform_structure(logger, properties)
        if document:
            annotate_limit_regulation(document, tcg_vector, ocg_vector)
            if assignments:
                annotate_assignments(document, assignments)
            if ko_overrides:
                override_ko(document, ko_overrides)
            write_output(yaml, logger, document)
            if return_results:
                results.append(document)
    if return_results:
        return results
