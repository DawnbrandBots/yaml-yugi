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
	const missingKoreanTranslation = [];
	for (const file of files) {
		if (file.endsWith(".json")) {
			const card = JSON.parse(await fs.promises.readFile(path.join(process.argv[2], file), "utf8"));
			if (!card.name.ko) {
				missingKoreanTranslation.push(card);
			}
		}
	}
	if (missingKoreanTranslation.length) {
		console.log(`yugipedia_page_id\tkonami_id\tpassword\tfake_password\tname.en\tname.ja`);
		for (const card of missingKoreanTranslation) {
			console.log(
				`${card.yugipedia_page_id}\t${card.konami_id}\t${card.password}\t${card.fake_password}\t[${card.name.en}]\t[${card.name.ja}]`
			);
		}
		process.exit(2);
	}
})();
