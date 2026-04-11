/**
 * Rebuild grocery list: delete existing items and re-add a clean set.
 *
 * Reads a plan from stdin (output of scripts/rebuild_grocery.py):
 *   {
 *     "delete_ids": ["id1", "id2", ...],
 *     "add_items": [{"name": "...", "quantity": "2 lbs", "details": "..."}, ...],
 *     "list_name": "My Grocery List"
 *   }
 *
 * Usage:
 *   python scripts/rebuild_grocery.py | node backend/tools/anylist/rebuild_list.js
 *
 * Env vars required: ANYLIST_EMAIL, ANYLIST_PASSWORD
 */

console.log = (...args) => process.stderr.write(args.join(' ') + '\n');

import AnyList from 'anylist';

const { ANYLIST_EMAIL, ANYLIST_PASSWORD } = process.env;
if (!ANYLIST_EMAIL || !ANYLIST_PASSWORD) {
  process.stderr.write('ANYLIST_EMAIL and ANYLIST_PASSWORD must be set\n');
  process.exit(1);
}

let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', chunk => { raw += chunk; });
process.stdin.on('end', async () => {
  const { delete_ids, add_items, list_name = 'My Grocery List' } = JSON.parse(raw);

  const client = new AnyList({ email: ANYLIST_EMAIL, password: ANYLIST_PASSWORD, credentialsFile: null });

  try {
    await client.login(false);
    await client.getLists();

    const list = client.getListByName(list_name);
    if (!list) {
      process.stderr.write(`List not found: "${list_name}"\n`);
      process.exit(1);
    }

    // Build category lookup from all known items across every list
    const categoryLookup = new Map();
    for (const lst of client.lists) {
      for (const item of lst.items || []) {
        if (item.categoryMatchId && item.categoryMatchId !== 'other') {
          categoryLookup.set(item.name.toLowerCase(), item.categoryMatchId);
        }
      }
    }

    function guessCategory(name) {
      const lower = name.toLowerCase();
      if (categoryLookup.has(lower)) return categoryLookup.get(lower);
      let best = 'other';
      let bestLen = 0;
      for (const [known, cat] of categoryLookup) {
        if (lower.includes(known) && known.length > bestLen) {
          best = cat;
          bestLen = known.length;
        }
      }
      return best;
    }

    // Delete existing items
    const deleteSet = new Set(delete_ids);
    let deleted = 0;
    for (const item of [...(list.items || [])]) {
      if (deleteSet.has(item.identifier)) {
        await list.removeItem(item);
        deleted++;
      }
    }
    process.stderr.write(`Deleted ${deleted} items\n`);

    // Re-add clean items
    let added = 0;
    for (const ing of add_items) {
      const categoryMatchId = guessCategory(ing.name);
      const itemOpts = {
        name: ing.name,
        details: ing.details ?? '',
        categoryMatchId,
      };
      if (ing.quantity) {
        itemOpts.deprecatedQuantity = ing.quantity;
      }
      const item = client.createItem(itemOpts);
      await list.addItem(item);
      process.stderr.write(`  + ${ing.name}${ing.quantity ? ` (${ing.quantity})` : ''} → ${categoryMatchId}\n`);
      added++;
    }

    process.stdout.write(JSON.stringify({ deleted, added }) + '\n');
    process.stderr.write(`Done. Deleted: ${deleted}, added: ${added}\n`);
  } catch (err) {
    process.stderr.write(`Error: ${err.message}\n`);
    process.exit(1);
  }
});
