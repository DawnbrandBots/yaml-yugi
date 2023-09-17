# SPDX-FileCopyrightText: © 2023 Kevin Lu
# SPDX-Licence-Identifier: AGPL-3.0-or-later
import logging
from multiprocessing import current_process
import os
from typing import Any, Dict, Optional

from ruamel.yaml import YAML

from common import initial_parse, int_or_og

module_logger = logging.getLogger(__name__)


def job(filepath: str) -> Optional[Dict[str, Any]]:
    yaml = YAML()
    basename = os.path.splitext(os.path.basename(filepath))[0]
    page_id = int_or_og(basename)
    logger = module_logger.getChild(current_process().name).getChild(basename)
    logger.info(filepath)
    wikitext = initial_parse(yaml, filepath, "Master Duel card")
    if not wikitext:
        logger.info("Skip")
        return
    wikitext["yugipedia_page_id"] = page_id
    return wikitext
