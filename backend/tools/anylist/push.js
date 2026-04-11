/**
 * AnyList ingredient push helper.
 * Reads a JSON payload from stdin, pushes ingredients to the Groceries list.
 *
 * Input (stdin, JSON):
 *   {
 *     "ingredients": [{ "name": "1 lb ground beef", "notes": "Baked Meatballs" }, ...],
 *     "list_name": "Groceries"   // optional, defaults to "Groceries"
 *   }
 *
 * Output (stdout, JSON):
 *   { "added": [...], "skipped": [...], "unchecked": [...] }
 *
 * Setup (server):
 *   cd backend/tools/anylist && npm install
 *   # Then apply protobuf patch:
 *   # node_modules/anylist/lib/item.js ~line 71: change `quantity` to `deprecatedQuantity`
 *
 * Env vars required: ANYLIST_EMAIL, ANYLIST_PASSWORD
 */

// Redirect console.log to stderr so only our JSON result goes to stdout
console.log = (...args) => process.stderr.write(args.join(' ') + '\n');

import AnyList from 'anylist';

const { ANYLIST_EMAIL, ANYLIST_PASSWORD } = process.env;
if (!ANYLIST_EMAIL || !ANYLIST_PASSWORD) {
  process.stderr.write('ANYLIST_EMAIL and ANYLIST_PASSWORD must be set\n');
  process.exit(1);
}

let raw = '';
process.stdin.setEncoding('utf8');
process.stdin.on('data', (chunk) => { raw += chunk; });
process.stdin.on('end', async () => {
  let payload;
  try {
    payload = JSON.parse(raw);
  } catch {
    process.stderr.write('Invalid JSON on stdin\n');
    process.exit(1);
  }

  const { ingredients = [], list_name = 'Groceries' } = payload;
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
    const categoryLookup = new Map(); // lowercase name → categoryMatchId
    for (const lst of client.lists) {
      for (const item of lst.items || []) {
        if (item.categoryMatchId && item.categoryMatchId !== 'other') {
          categoryLookup.set(item.name.toLowerCase(), item.categoryMatchId);
        }
      }
    }

    function guessCategory(ingredientName) {
      const lower = ingredientName.toLowerCase();
      if (categoryLookup.has(lower)) return categoryLookup.get(lower);
      // Longest-substring match: prefer more specific known names
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

    const added = [];
    const skipped = [];
    const unchecked = [];

    for (const ing of ingredients) {
      const itemName = ing.name;
      if (!itemName) continue;

      const existing = list.getItemByName(itemName);
      if (existing) {
        if (existing.checked) {
          existing.checked = false;
          await existing.save();
          unchecked.push(itemName);
        } else {
          skipped.push(itemName);
        }
        continue;
      }

      const categoryMatchId = guessCategory(itemName);
      const itemOpts = { name: itemName, details: ing.notes ?? '', categoryMatchId };
      if (ing.quantity) itemOpts.deprecatedQuantity = ing.quantity;
      const item = client.createItem(itemOpts);
      await list.addItem(item);
      added.push(itemName);
    }

    process.stdout.write(JSON.stringify({ added, skipped, unchecked }) + '\n');
  } catch (err) {
    process.stderr.write(`AnyList error: ${err.message}\n`);
    process.exit(1);
  }
});
