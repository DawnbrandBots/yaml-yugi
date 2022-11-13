# SPDX-FileCopyrightText: © 2022 Kevin Lu
# SPDX-Licence-Identifier: AGPL-3.0-or-later
from argparse import ArgumentParser
import json
import logging
import math
import os

from job_ocgtcg import job


parser = ArgumentParser()
parser.add_argument("wikitext_directory", help="yaml-yugipedia card texts")
parser.add_argument("--assignments", help="fake password assignment YAML")
parser.add_argument("--zh-CN", help="yaml-yugi-zh card texts")
parser.add_argument("--tcg", help="TCG Forbidden & Limited List, Konami ID vector JSON")
parser.add_argument("--ocg", help="OCG Forbidden & Limited List, English name vector JSON")
parser.add_argument("--ko", help="yaml-yugi-ko overrides.tsv")
parser.add_argument("--generate-schema", action="store_true", help="output generated JSON schema file")
parser.add_argument("--processes", type=int, default=0, help="number of worker processes, default ncpu")
parser.add_argument("--aggregate", help="output aggregate JSON file")

logger = logging.getLogger(__name__)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    args = parser.parse_args()
    processes = args.processes
    if processes == 0:
        processes = os.cpu_count()
        logger.info(f"Using {processes} processes.")

    tcg = None
    ocg = None
    if args.tcg:
        with open(args.tcg) as f:
            tcg = json.load(f)
    if args.ocg:
        with open(args.ocg) as f:
            ocg = json.load(f)

    files = [
        filename for filename in
        os.listdir(args.wikitext_directory)
        if os.path.isfile(os.path.join(args.wikitext_directory, filename))
    ]

    if processes == 1:
        cards = job(args.wikitext_directory, files, args.zh_CN, args.assignments, tcg, ocg, args.ko, args.aggregate is not None)
    else:
        size = math.ceil(len(files) / processes)
        partitions = [files[i:i+size] for i in range(0, len(files), size)]
        cards = []

        from multiprocessing import Pool
        with Pool(processes) as pool:
            jobs = [
                pool.apply_async(job, (args.wikitext_directory, partition,
                                       args.zh_CN, args.assignments, tcg, ocg, args.ko, args.aggregate is not None))
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
