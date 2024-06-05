# SPDX-FileCopyrightText: © 2023 Kevin Lu
# SPDX-Licence-Identifier: AGPL-3.0-or-later
from argparse import ArgumentParser
import json
import logging
import os
import sys

from job_masterduel import job

parser = ArgumentParser()
parser.add_argument("wikitext_directory", help="yaml-yugipedia card texts")
parser.add_argument(
    "--processes", type=int, default=0, help="number of worker processes, default ncpu"
)

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = parser.parse_args()
    processes = args.processes
    if processes == 0:
        processes = os.cpu_count()
        logger.info(f"Using {processes} processes.")

    files = [
        os.path.join(args.wikitext_directory, filename)
        for filename in os.listdir(args.wikitext_directory)
        if os.path.isfile(os.path.join(args.wikitext_directory, filename))
    ]
    if processes == 1:
        cards = map(job, files)
    else:
        from multiprocessing import Pool

        with Pool(processes) as pool:
            cards = [card for card in pool.imap_unordered(job, files, 100) if card]

    logger.info("Serializing to JSON")
    json.dump(cards, sys.stdout)


if __name__ == "__main__":
    main()
