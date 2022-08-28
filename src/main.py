from argparse import ArgumentParser
import math
import os

from job import job


parser = ArgumentParser()
parser.add_argument("wikitext_directory", help="yaml-yugipedia card texts")
parser.add_argument("--assignments", help="fake password assignment YAML")
parser.add_argument("--zh-CN", help="yaml-yugi-zh card texts")
parser.add_argument("--ko", help="yaml-yugi-ko TBD")
parser.add_argument("--generate-schema", action="store_true", help="output generated JSON schema file")
parser.add_argument("--processes", type=int, default=0, help="number of worker processes, default ncpu")


def main() -> None:
    args = parser.parse_args()
    processes = args.processes
    if processes == 0:
        processes = os.cpu_count()

    files = [
        filename for filename in
        os.listdir(args.wikitext_directory)
        if os.path.isfile(os.path.join(args.wikitext_directory, filename))
    ]

    if processes == 1:
        job(args.wikitext_directory, files, args.zh_CN)
    else:
        size = math.ceil(len(files) / processes)
        partitions = [files[i:i+size] for i in range(0, len(files), size)]

        from multiprocessing import Pool
        with Pool(processes) as pool:
            jobs = [
                pool.apply_async(job, (args.wikitext_directory, partition, args.zh_CN))
                for partition in partitions
            ]
            for result in jobs:
                result.get()


if __name__ == "__main__":
    main()
