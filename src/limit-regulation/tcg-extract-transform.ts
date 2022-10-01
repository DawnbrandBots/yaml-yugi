// SPDX-FileCopyrightText: © 2022 Kevin Lu
// SPDX-Licence-Identifier: AGPL-3.0-or-later

// Usage: curl --silent https://www.yugioh-card.com/uk/limited/ | grep 'jsonData =' | yarn ts-node src/limit-regulation/tcg-extract-transform.ts data/limit-regulation/tcg

import * as fs from "fs";
import { VM } from "vm2";

// ts-node --cwd doesn't work
if (process.argv.length > 2) {
	process.chdir(process.argv[2]);
}

const vm = new VM();
vm.runFile("/dev/stdin");
const data = vm.getGlobal("jsonData");

const [day, month, year] = data.from.split("/");
fs.writeFileSync(`${year}-${month}-${day}.raw.json`, `${JSON.stringify(data, null, 2)}\n`);

function extractId(card: Record<string, string>): string {
	const url = new URL(card.link);
	// The null case should never happen
	return url.searchParams.get("cid") ?? card.nameeng;
}

const result: Record<string, 0 | 1 | 2> = {};
for (const card of data["0"] ?? []) {
	result[extractId(card)] = 0;
}
for (const card of data["1"] ?? []) {
	result[extractId(card)] = 1;
}
for (const card of data["2"] ?? []) {
	result[extractId(card)] = 2;
}

fs.writeFileSync(`${year}-${month}-${day}.vector.json`, `${JSON.stringify(result, null, 2)}\n`);
