// SPDX-FileCopyrightText: © 2023–2024 Kevin Lu
// SPDX-Licence-Identifier: AGPL-3.0-or-later
import fs from "fs";
import path from "path";

if (process.argv.length < 4) {
	console.error(`Usage: ${process.argv[1]} <data/cards> <ko|ja>`);
	process.exit(1);
}

(async () => {
	const files = await fs.promises.readdir(process.argv[2]);
	const lang = process.argv[3];
	const missingNames = [];
	for (const file of files) {
		if (file.endsWith(".json")) {
			const card = JSON.parse(await fs.promises.readFile(path.join(process.argv[2], file), "utf8"));
			// Only consider cards with a Japanese print. This currently excludes the Rush Duel 2024 World Championship
			// match winner prize cards 20702 and 20703, which were only printed in English.
			if (!card.name[lang] && card.sets.ja) {
				missingNames.push(card);
			}
		}
	}
	if (missingNames.length) {
		console.log(`yugipedia_page_id\tkonami_id\tpassword\tfake_password\tname.en\tname.ja\tname.ko`);
		for (const card of missingNames) {
			console.log(
				`${card.yugipedia_page_id}\t${card.konami_id}\t${card.password}\t${card.fake_password}\t[${card.name.en}]\t[${card.name.ja}]\t[${card.name.ko}]`
			);
		}
		process.exit(2);
	}
})();
