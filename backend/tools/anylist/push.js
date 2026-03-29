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

      const item = client.createItem({ name: itemName, notes: ing.notes ?? '' });
      await list.addItem(item);
      added.push(itemName);
    }

    process.stdout.write(JSON.stringify({ added, skipped, unchecked }) + '\n');
  } catch (err) {
    process.stderr.write(`AnyList error: ${err.message}\n`);
    process.exit(1);
  }
});
