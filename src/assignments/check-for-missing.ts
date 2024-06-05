// SPDX-FileCopyrightText: © 2023 Kevin Lu
// SPDX-Licence-Identifier: AGPL-3.0-or-later
import fs from "fs";
import path from "path";

if (process.argv.length < 3) {
	console.error(`Usage: ${process.argv[1]} <data/cards>`);
	process.exit(1);
}

// https://yugipedia.com/wiki/Card_Number
// See also job_ocgtcg.py:annotate_assignments
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function isPrereleaseMissingCardNumber(card: any): boolean {
	const release = card.sets.ja?.length ? card.sets.ja[0] : card.sets.en?.length ? card.sets.en[0] : null;
	if (!release) {
		console.error(`ERROR: ${card.yugipedia_page_id}\t[${card.name.en}]\tNo JP or EN sets found!`);
		return true;
	}
	// Only need to check the last two characters to know if we have a number.
	// Skip the region code and the third character that may or may not be a digit.
	const position = release.set_number.split("-")[1].slice(3);
	const isMissing = isNaN(Number(position));
	if (isMissing) {
		console.warn(
			`WARNING: ${card.yugipedia_page_id}\t[${card.name.en}]\tNot counted due to unknown set position ${position}`
		);
	}
	return isMissing;
}

// Okay to skip these before print, e.g. Anotherverse Gluttonia
// eslint-disable-next-line @typescript-eslint/no-explicit-any
function isPrereleasePrizeCard(card: any): boolean {
	const release = card.sets.ja?.length ? card.sets.ja[0] : card.sets.en?.length ? card.sets.en[0] : null;
	const isPrizeCard = release?.set_number.split("-")[0] === "YCSW";
	if (isPrizeCard) {
		console.warn(`WARNING: ${card.yugipedia_page_id}\t[${card.name.en}]\tNot counted due to being a prize card`);
	}
	return isPrizeCard;
}

(async () => {
	const files = await fs.promises.readdir(process.argv[2]);
	const missingFakePasswords = [];
	for (const file of files) {
		if (file.endsWith(".json")) {
			const card = JSON.parse(await fs.promises.readFile(path.join(process.argv[2], file), "utf8"));
			if (
				!card.password &&
				!card.fake_password &&
				!isPrereleaseMissingCardNumber(card) &&
				!isPrereleasePrizeCard(card)
			) {
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
