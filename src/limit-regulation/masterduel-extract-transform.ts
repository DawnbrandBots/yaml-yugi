// SPDX-FileCopyrightText: © 2023 Kevin Lu
// SPDX-Licence-Identifier: AGPL-3.0-or-later

import * as fs from "fs";

(async () => {
    const cards = JSON.parse(await fs.promises.readFile(process.argv[2], { encoding: "utf-8" }));
    const enNameToKonamiID = new Map();
    for (const card of cards) {
        if (card.konami_id) {
            enNameToKonamiID.set(card.name.en, card.konami_id);
        }
    }

    const today = new Date();
    let effectiveDate = new Date(0);
    let current = "";
    const files = await fs.promises.readdir(".");
    for (const file of files) {
        if (file.endsWith(".name.json")) {
            const name = file.slice(0, 10);
            const raw = JSON.parse(await fs.promises.readFile(file, { encoding: "utf-8" }));
            const vector = Object.fromEntries(
                Object.entries(raw).map(([name, limit]) => ([enNameToKonamiID.get(name), limit]))
            );
            const vectorFile = `${name}.vector.json`;
            await fs.promises.writeFile(vectorFile, JSON.stringify(vector, null, 2) + "\n");
            const date = new Date(name);
            if (date < today && date > effectiveDate) {
                effectiveDate = date;
                current = vectorFile;
            }
        }
    }
    console.log(`Currently effective: ${effectiveDate}`);
    await fs.promises.unlink("current.vector.json").catch(console.error);
    await fs.promises.symlink(current, "current.vector.json");
})();
