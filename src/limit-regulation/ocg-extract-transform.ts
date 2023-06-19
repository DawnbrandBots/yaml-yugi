// SPDX-FileCopyrightText: © 2023 Kevin Lu
// SPDX-Licence-Identifier: AGPL-3.0-or-later

import * as fs from "fs";
import got from "got";
import { parseDocument } from "htmlparser2";
import type { Element } from "domhandler";
import { selectAll } from "css-select";

const fetch = got.extend({ timeout: 10000, hooks: {
	beforeRequest: [
		request => {
			console.log(`Fetching ${request.url}`);
		}
	],
} });

(async () => {
	// const jpIndex = await fetch("https://www.yugioh-card.com/japan/event/rankingduel/limitregulation/");
    // const jpHtml = parseDocument(jpIndex.body);
    // const jpLinks = selectAll("a.event", jpHtml as unknown as Element);
    // const jpDates = jpLinks.map(element => parseInt(element.attribs.href.slice(6)));

    const hkIndex = await fetch("https://www.yugioh-card.com/hk/event/rules_guides/forbidden_cardlist.php");
    const hkHtml = parseDocument(hkIndex.body);
    const hkLinks = selectAll("a.to_event", hkHtml as unknown as Element);
    const hkDates = hkLinks.map(element => parseInt(element.attribs.href.slice(6)));
    await Promise.all([
        hkDates.map(date => fetch(`https://www.yugioh-card.com/hk/data/forbidden_card_lists/${date}.csv`)
            // CSVs 202104 and prior are encoded in Shift_JIS rather than Unicode
            .then(response => fs.promises.writeFile(`${date}.csv`, response.rawBody)))
    ]);
})();
