# SPDX-FileCopyrightText: © 2022–2025 Kevin Lu
# SPDX-Licence-Identifier: AGPL-3.0-or-later
import json
import logging
from multiprocessing import current_process
import os
import sys
from typing import Any, Dict, List, NamedTuple, Optional, Union

from ruamel.yaml import YAML
from ruamel.yaml.scalarstring import LiteralScalarString

from common import (
    annotate_shared,
    initial_parse,
    int_or_none,
    int_or_og,
    replace_interlinear_annotations,
    transform_image,
    transform_names,
    transform_sets,
    transform_multilanguage,
    write,
    load_ko_csv,
    load_unreleased_csv,
)

module_logger = logging.getLogger(__name__)


def annotate_zh_cn(
    yaml: YAML, logger: logging.Logger, document: Dict[str, str], zh_cn_dir: str
) -> None:
    if document["name"]["zh-CN"] and document["text"]["zh-CN"]:
        return
    password = int_or_none(document.get("password") or "")
    zh_cn_path = os.path.join(zh_cn_dir, f"{password}.yaml")
    if os.path.isfile(zh_cn_path):
        logger.info(f"zh-CN: {zh_cn_path}")
        with open(zh_cn_path) as f:
            zh_cn = yaml.load(f)
            if not document["name"]["zh-CN"]:
                document["name"]["zh-CN"] = zh_cn["name"]
            if not document["text"]["zh-CN"]:
                document["text"]["zh-CN"] = LiteralScalarString(zh_cn["text"])
            if (
                document.get("pendulum_effect")
                and not document["pendulum_effect"]["zh-CN"]
                and zh_cn.get("pendulum")
            ):
                document["pendulum_effect"]["zh-CN"] = LiteralScalarString(
                    zh_cn["pendulum"]
                )


def transform_structure(
    logger: logging.Logger, wikitext: Dict[str, str]
) -> Optional[Dict[str, Any]]:
    if (
        # Normal monster version OCG prize cards, Tyler, OG Egyptian Gods
        wikitext.get("database_id") == "none"
        or
        # Match winners, Command Duel-Use Card (only one with dbid None), etc. have db ids but no passwords
        "limitation_text" in wikitext
        or
        # Boss Duel cards
        wikitext.get("jp_sets", "").startswith("BD-JP")
        or
        # Deprecated: https://yugipedia.com/wiki/Category:Cards_with_a_manual_status
        wikitext.get("ocg_status") == "Illegal"
        or
        # Details unavailable for a new leak
        wikitext.get("level") == "???"
        or wikitext.get("attribute") == "???"
        or wikitext.get("atk") == "???"
        or wikitext.get("def") == "???"
        or wikitext.get("card_type") == "???"
        or wikitext.get("property") == "???"
        or wikitext.get("lore") == "TBA"
        or
        # Rush Duel cards erroneously added to the Duel Monsters category
        "RD/" in wikitext.get("jp_sets", "")
    ):
        logger.info(f"Skip: {wikitext}")
        return
    konami_id = int_or_none(wikitext.get("database_id"))
    password = int_or_none(wikitext.get("password"))
    document = {
        "konami_id": konami_id,
        "password": password,
        "name": transform_names(wikitext),
        "text": transform_multilanguage(wikitext, "text"),
    }
    annotate_shared(document, wikitext)
    if wikitext.get("image"):
        document["images"] = transform_image(wikitext.get("image"))
    document["sets"] = transform_sets(wikitext)
    document["limit_regulation"] = {
        "tcg": wikitext.get("tcg_status"),
        "ocg": wikitext.get("ocg_status"),
    }
    if "tcg_speed_duel_status" in wikitext:
        document["limit_regulation"]["speed"] = wikitext["tcg_speed_duel_status"]
    if "is_translation_unofficial" in wikitext:
        document["is_translation_unofficial"] = wikitext["is_translation_unofficial"]
    document["yugipedia_page_id"] = wikitext["yugipedia_page_id"]
    return document


LIMIT_REGULATION_MAPPING = {
    0: "Forbidden",
    1: "Limited",
    2: "Semi-Limited",
    None: "Unlimited",
}


def annotate_limit_regulation(
    document: Dict[str, Any],
    unreleased: Dict[str, Dict[str, str]],
    tcg_vector: Optional[Dict[str, int]],
    ocg_vector: Optional[Dict[str, int]],
) -> None:
    if (
        (release := unreleased.get(document["name"]["en"]))
        # Exclude The Seal of Orichalcos (UDE promo) and some others
        and (ocg := release.get("OCG status")) != "Illegal"
        and (tcg := release.get("TCG status")) != "Illegal"
    ):
        document["limit_regulation"]["tcg"] = tcg or "Not yet released"
        document["limit_regulation"]["ocg"] = ocg or "Not yet released"
        if speed := release.get("TCG Speed Duel status"):
            document["limit_regulation"]["speed"] = speed
    if (
        tcg_vector
        and document["konami_id"]
        and document["limit_regulation"]["tcg"] != "Not yet released"
        and "en" in document["sets"]
    ):
        document["limit_regulation"]["tcg"] = LIMIT_REGULATION_MAPPING[
            tcg_vector.get(str(document["konami_id"]))
        ]
    if (
        ocg_vector
        and document["konami_id"]
        and document["limit_regulation"]["ocg"] != "Not yet released"
        and "ja" in document["sets"]
    ):
        document["limit_regulation"]["ocg"] = LIMIT_REGULATION_MAPPING[
            ocg_vector.get(str(document["konami_id"]))
        ]


def write_output(yaml: YAML, logger: logging.Logger, document: Dict[str, Any]) -> None:
    if document["password"] is not None:
        # Recreate eight-digit password with left-padded 0s
        basename = str(document["password"]).rjust(8, "0")
    elif document["konami_id"] is not None:
        basename = f"kdb{document['konami_id']}"
    else:
        basename = f"yugipedia{document['yugipedia_page_id']}"
    write(document, basename, yaml, logger)


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
            assignments.set_abbreviation[item["set_abbreviation"]] = item[
                "fake_password_range"
            ]
    return assignments


def annotate_assignments(document: Dict[str, Any], assignments: Assignments) -> None:
    # Direct assignment, may be used for certain passwordless cards or individual prereleases
    page_id = document["yugipedia_page_id"]
    if page_id in assignments.yugipedia:
        document["fake_password"] = assignments.yugipedia[page_id]
        return

    # Prerelease password assignment by set
    if document["password"] is None:
        if len(document["sets"].get("ja", [])):
            release = document["sets"]["ja"][0]
        elif len(document["sets"].get("en", [])):
            release = document["sets"]["en"][0]
        else:
            return
        # https://yugipedia.com/wiki/Card_Number
        # one-character region codes and two-digit position numbers are no longer a thing
        set_abbreviation, position = release["set_number"].split("-")
        if set_abbreviation in assignments.set_abbreviation:
            # Typically, three digits follow the region code, e.g. EN100, but some
            # special cards use an additional letter, e.g. JPPO1, JPN01, JPS01
            start = 2 if position[2].isdigit() else 3
            try:
                position = int(position[start:])
                if isinstance(assignments.set_abbreviation[set_abbreviation], int):
                    document["fake_password"] = (
                        position + assignments.set_abbreviation[set_abbreviation]
                    )
                else:  # list
                    document["fake_password"] = [
                        position + fake_range
                        for fake_range in assignments.set_abbreviation[set_abbreviation]
                    ]
            except ValueError as e:
                # Typically unknown card number like 0??
                module_logger.warn(document["yugipedia_page_id"], exc_info=e)


def mixin_text(
    pkey: str,
    ckey: str,
    skey: str,
    document: Dict[str, Any],
    master_duel_card: Dict[str, Any],
    logger: logging.Logger,
) -> None:
    if not document[pkey][ckey]:
        source = master_duel_card.get(skey)
        if source and source != ".":
            logger.info(f"Merging in Master Duel {pkey}.{ckey}")
            if pkey == "text" or pkey == "pendulum_effect":
                document[pkey][ckey] = LiteralScalarString(source)
            else:
                document[pkey][ckey] = source


def annotate_master_duel(
    logger: logging.Logger, document: Dict[str, Any], master_duel: Dict[str, Any]
) -> None:
    name = document["name"]["en"]
    master_duel_card = master_duel.get(name)
    # Skip Normal Monster version of Black Luster Soldier since will match the Ritual Monster
    if master_duel_card and document["konami_id"] != 19092:
        logger.info(f"Annotating [{name}] with Master Duel data")
        document["master_duel_rarity"] = master_duel_card["rarity"]
        mixin_text("name", "de", "de_name", document, master_duel_card, logger)
        mixin_text("name", "es", "es_name", document, master_duel_card, logger)
        mixin_text("name", "fr", "fr_name", document, master_duel_card, logger)
        mixin_text("name", "it", "it_name", document, master_duel_card, logger)
        mixin_text("name", "pt", "pt_name", document, master_duel_card, logger)
        mixin_text("name", "ja", "ja_name", document, master_duel_card, logger)
        mixin_text("name", "ko", "ko_name", document, master_duel_card, logger)
        mixin_text("name", "zh-TW", "tc_name", document, master_duel_card, logger)
        mixin_text("name", "zh-CN", "sc_name", document, master_duel_card, logger)
        mixin_text("text", "de", "de_lore", document, master_duel_card, logger)
        mixin_text("text", "es", "es_lore", document, master_duel_card, logger)
        mixin_text("text", "fr", "fr_lore", document, master_duel_card, logger)
        mixin_text("text", "it", "it_lore", document, master_duel_card, logger)
        mixin_text("text", "pt", "pt_lore", document, master_duel_card, logger)
        mixin_text("text", "ja", "ja_lore", document, master_duel_card, logger)
        mixin_text("text", "ko", "ko_lore", document, master_duel_card, logger)
        mixin_text("text", "zh-TW", "tc_lore", document, master_duel_card, logger)
        mixin_text("text", "zh-CN", "sc_lore", document, master_duel_card, logger)
        if document.get("pendulum_effect"):
            mixin_text(
                "pendulum_effect",
                "de",
                "de_pendulum_effect",
                document,
                master_duel_card,
                logger,
            )
            mixin_text(
                "pendulum_effect",
                "es",
                "es_pendulum_effect",
                document,
                master_duel_card,
                logger,
            )
            mixin_text(
                "pendulum_effect",
                "fr",
                "fr_pendulum_effect",
                document,
                master_duel_card,
                logger,
            )
            mixin_text(
                "pendulum_effect",
                "it",
                "it_pendulum_effect",
                document,
                master_duel_card,
                logger,
            )
            mixin_text(
                "pendulum_effect",
                "pt",
                "pt_pendulum_effect",
                document,
                master_duel_card,
                logger,
            )
            mixin_text(
                "pendulum_effect",
                "ja",
                "ja_pendulum_effect",
                document,
                master_duel_card,
                logger,
            )
            mixin_text(
                "pendulum_effect",
                "ko",
                "ko_pendulum_effect",
                document,
                master_duel_card,
                logger,
            )
            mixin_text(
                "pendulum_effect",
                "zh-TW",
                "tc_pendulum_effect",
                document,
                master_duel_card,
                logger,
            )
            mixin_text(
                "pendulum_effect",
                "zh-CN",
                "sc_pendulum_effect",
                document,
                master_duel_card,
                logger,
            )


def replace_text(
    pkey: str,
    ckey: str,
    skey: str,
    document: Dict[str, Any],
    official_card: Dict[str, str],
    logger: logging.Logger,
) -> None:
    # CSV only has empty strings, but null is preferred for YAML and JSON
    source = official_card[skey] or None
    if document[pkey][ckey] != source:
        logger.info(
            f"{pkey}.{ckey} does not match: O[{source}] Y[{document[pkey][ckey]}]"
        )
        if pkey == "text" or pkey == "pendulum_effect":
            document[pkey][ckey] = LiteralScalarString(source)
        else:
            document[pkey][ckey] = source


def replace_with_official(
    logger: logging.Logger,
    document: Dict[str, Any],
    official: Dict[int, Dict[str, str]],
    lang: str,
) -> None:
    kid = document["konami_id"]
    if kid and official.get(kid):
        logger.info(f"{kid}: replacing {lang} text with official database")
        replace_text("name", lang, "name", document, official[kid], logger)
        replace_text("text", lang, "text", document, official[kid], logger)
        if document.get("pendulum_effect"):
            replace_text(
                "pendulum_effect", lang, "pendulum", document, official[kid], logger
            )


def override_ko(
    logger: logging.Logger,
    document: Dict[str, Any],
    ko_override: Dict[int, Dict[str, str]],
) -> None:
    kid = document["konami_id"]
    if kid and ko_override.get(kid):
        module_logger.info(f"APPLYING OVERRIDE FOR {kid}")
        if ko_override[kid]["name"]:
            logger.info(f"{kid}: overriding name.ko")
            document["name"]["ko"] = replace_interlinear_annotations(
                ko_override[kid]["name"]
            )
        if ko_override[kid]["text"]:
            logger.info(f"{kid}: overriding text.ko")
            document["text"]["ko"] = LiteralScalarString(ko_override[kid]["text"])
        if ko_override[kid]["pendulum"]:
            logger.info(f"{kid}: overriding pendulum_effect.ko")
            document["pendulum_effect"]["ko"] = LiteralScalarString(
                ko_override[kid]["pendulum"]
            )


def job(
    wikitext_dir: str,
    filenames: List[str],
    zh_cn_dir: Optional[str] = None,
    assignment_file: Optional[str] = None,
    tcg_vector: Optional[Dict[str, int]] = None,
    ocg_vector: Optional[Dict[str, int]] = None,
    unreleased_csv: Optional[str] = None,
    ko_official_csv: Optional[str] = None,
    ko_override_csv: Optional[str] = None,
    ko_prerelease_csv: Optional[str] = None,
    master_duel_raw_json: Optional[str] = None,
    return_results=False,
) -> Optional[List[Dict[str, Any]]]:
    yaml = YAML()
    yaml.width = sys.maxsize
    assignments = load_assignments(yaml, assignment_file) if assignment_file else None
    unreleased = load_unreleased_csv(unreleased_csv)
    ko_official = load_ko_csv("konami_id", ko_official_csv)
    ko_override = load_ko_csv("konami_id", ko_override_csv)
    ko_prerelease = load_ko_csv("yugipedia_page_id", ko_prerelease_csv)  # noqa: F841
    job_logger = module_logger.getChild(current_process().name)
    if master_duel_raw_json:
        with open(master_duel_raw_json) as f:
            raw = json.load(f)
            master_duel = {}
            for card in raw:
                key = card["en_name"]
                # Edge cases where the Master Duel name differs for some reason (as of writing, Maliss and Reactor)
                if "main" in card and not card["main"].endswith(" (card)"):
                    job_logger.info(f"[{key} (Master Duel)] is [{card['main']}]")
                    key = card["main"]
                master_duel[key] = card
    else:
        master_duel = None
    results = []
    for i, filename in enumerate(filenames):
        filepath = os.path.join(wikitext_dir, filename)
        # This should always be int, but code defensively and allow future changes to yaml-yugipedia's structure
        basename = os.path.splitext(filename)[0]
        page_id = int_or_og(basename)
        logger = job_logger.getChild(basename)
        logger.info(f"{i}/{len(filenames)} {filepath}")

        properties = initial_parse(yaml, filepath)
        if not properties:
            logger.info(f"Skip: {filepath}")
            continue
        properties["yugipedia_page_id"] = page_id
        document = transform_structure(logger, properties)
        if document:
            annotate_limit_regulation(document, unreleased, tcg_vector, ocg_vector)
            if ko_official:
                replace_with_official(logger, document, ko_official, "ko")
            if master_duel:
                annotate_master_duel(logger, document, master_duel)
            if assignments:
                annotate_assignments(document, assignments)
            if ko_override:
                override_ko(logger, document, ko_override)
            if zh_cn_dir:
                annotate_zh_cn(yaml, logger, document, zh_cn_dir)
            write_output(yaml, logger, document)
            if return_results:
                results.append(document)
    if return_results:
        return results
