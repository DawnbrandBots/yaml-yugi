# SPDX-FileCopyrightText: © 2022–2024 Kevin Lu
# SPDX-Licence-Identifier: AGPL-3.0-or-later
from argparse import ArgumentParser
import json
import logging
import math
import os

from job_rush import job


parser = ArgumentParser()
parser.add_argument("wikitext_directory", help="yaml-yugipedia card texts")
parser.add_argument("--ko-official", help="yaml-yugi-ko official database CSV")
parser.add_argument("--ko-override", help="yaml-yugi-ko rush-override.csv")
parser.add_argument("--ko-prerelease", help="yaml-yugi-ko rush-prerelease.csv")
parser.add_argument("--ocg-aggregate", help="cards.json")
parser.add_argument(
    "--generate-schema", action="store_true", help="output generated JSON schema file"
)
parser.add_argument(
    "--processes", type=int, default=0, help="number of worker processes, default ncpu"
)
parser.add_argument("--aggregate", help="output aggregate JSON file")

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = parser.parse_args()
    processes = args.processes
    if processes == 0:
        processes = os.cpu_count()
        logger.info(f"Using {processes} processes.")

    files = [
        filename
        for filename in os.listdir(args.wikitext_directory)
        if os.path.isfile(os.path.join(args.wikitext_directory, filename))
    ]

    arguments = (
        args.ko_official,
        args.ko_override,
        args.ko_prerelease,
        args.ocg_aggregate,
        args.aggregate is not None,
    )
    if processes == 1:
        cards = job(args.wikitext_directory, files, *arguments)
    else:
        size = math.ceil(len(files) / processes)
        partitions = [files[i : i + size] for i in range(0, len(files), size)]
        cards = []

        from multiprocessing import Pool

        with Pool(processes) as pool:
            jobs = [
                pool.apply_async(job, (args.wikitext_directory, partition, *arguments))
                for partition in partitions
            ]
            for result in jobs:
                chunk = result.get()
                if args.aggregate is not None:
                    cards.extend(chunk)

    if args.aggregate is not None:
        logger.info(f"Write: {args.aggregate}")
        with open(args.aggregate, "w", encoding="utf-8") as out:
            json.dump(cards, out)


if __name__ == "__main__":
    main()
