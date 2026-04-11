/**
 * One-time script to backfill categoryMatchId on grocery list items stuck in "other".
 *
 * Builds a category lookup from all items across every list that already have
 * a known category, then applies longest-substring matching to items on the
 * target list that are currently uncategorized (categoryMatchId === "other").
 *
 * Usage (on server, from backend/tools/anylist/):
 *   ANYLIST_EMAIL=... ANYLIST_PASSWORD=... node recategorize.js [list_name]
 *   list_name defaults to "My Grocery List"
 */

// Redirect console.log to stderr so stdout stays clean
console.log = (...args) => process.stderr.write(args.join(' ') + '\n');

import AnyList from 'anylist';

const { ANYLIST_EMAIL, ANYLIST_PASSWORD } = process.env;
if (!ANYLIST_EMAIL || !ANYLIST_PASSWORD) {
  process.stderr.write('ANYLIST_EMAIL and ANYLIST_PASSWORD must be set\n');
  process.exit(1);
}

const list_name = process.argv[2] ?? 'My Grocery List';

const client = new AnyList({ email: ANYLIST_EMAIL, password: ANYLIST_PASSWORD, credentialsFile: null });

try {
  await client.login(false);
  await client.getLists();

  // Build category lookup from all items that already have a real category
  const categoryLookup = new Map();
  for (const lst of client.lists) {
    for (const item of lst.items || []) {
      if (item.categoryMatchId && item.categoryMatchId !== 'other') {
        categoryLookup.set(item.name.toLowerCase(), item.categoryMatchId);
      }
    }
  }
  process.stderr.write(`Built category lookup: ${categoryLookup.size} known items\n`);

  function guessCategory(name) {
    const lower = name.toLowerCase();
    if (categoryLookup.has(lower)) return categoryLookup.get(lower);
    let best = null;
    let bestLen = 0;
    for (const [known, cat] of categoryLookup) {
      if (lower.includes(known) && known.length > bestLen) {
        best = cat;
        bestLen = known.length;
      }
    }
    return best;
  }

  const list = client.getListByName(list_name);
  if (!list) {
    process.stderr.write(`List not found: "${list_name}"\n`);
    process.exit(1);
  }

  const activeItems = (list.items || []).filter(i => !i.checked);
  const uncategorized = activeItems.filter(i => !i.categoryMatchId || i.categoryMatchId === 'other');
  process.stderr.write(`Active items: ${activeItems.length}, uncategorized: ${uncategorized.length} in "${list_name}"\n`);

  const updated = [];
  const unmatched = [];

  for (const item of uncategorized) {
    const cat = guessCategory(item.name);
    if (cat) {
      try {
        item.categoryMatchId = cat;
        await item.save();
        updated.push({ name: item.name, category: cat });
        process.stderr.write(`  OK: "${item.name}" → ${cat}\n`);
      } catch (err) {
        process.stderr.write(`  FAIL: "${item.name}" → ${err.message}\n`);
        unmatched.push(item.name + ' [save failed]');
      }
    } else {
      unmatched.push(item.name);
    }
  }

  process.stdout.write(JSON.stringify({ updated, unmatched }, null, 2) + '\n');
  process.stderr.write(`Done. Updated: ${updated.length}, no match: ${unmatched.length}\n`);
} catch (err) {
  process.stderr.write(`Error: ${err.message}\n`);
  process.exit(1);
}
