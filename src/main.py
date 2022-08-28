from argparse import ArgumentParser


parser = ArgumentParser()
parser.add_argument("wikitext_directory", help="yaml-yugipedia card texts")
parser.add_argument("--assignments", help="fake password assignment YAML")
parser.add_argument("--zh-CN", help="yaml-yugi-zh card texts")
parser.add_argument("--ko", help="yaml-yugi-ko TBD")
parser.add_argument("--generate-schema", action="store_true", help="output generated JSON schema file")
parser.add_argument("--processes", type=int, default=0, help="number of worker processes, default ncpu")
parser.parse_args()
