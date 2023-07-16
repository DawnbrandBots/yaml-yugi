// SPDX-FileCopyrightText: © 2023 Kevin Lu
// SPDX-Licence-Identifier: AGPL-3.0-or-later
import fs from "fs";
import path from "path";

if (process.argv.length < 3) {
	console.error(`Usage: ${process.argv[1]} <data/cards>`);
	process.exit(1);
}

(async () => {
	const files = await fs.promises.readdir(process.argv[2]);
	const missingFakePasswords = [];
	for (const file of files) {
		if (file.endsWith(".json")) {
			const card = JSON.parse(await fs.promises.readFile(path.join(process.argv[2], file), "utf8"));
			if (!card.password && !card.fake_password) {
				missingFakePasswords.push(card);
			}
		}
	}
	if (missingFakePasswords.length) {
		for (const card of missingFakePasswords) {
			console.log(`${card.yugipedia_page_id}\t[${card.name.en}]`);
		}
		process.exit(2);
	}
})();
