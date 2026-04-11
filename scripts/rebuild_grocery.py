#!/usr/bin/env python3
"""
Parse messy grocery list items via Haiku and output a rebuild plan as JSON.

Usage (on server, from project root with venv active):
  python scripts/rebuild_grocery.py | node backend/tools/anylist/rebuild_list.js

Outputs JSON to stdout: { "delete_ids": [...], "add_items": [{name, quantity, details}] }
"""

import json
import os
import sys
from anthropic import Anthropic

client = Anthropic()

# All 48 unchecked item IDs — every one gets deleted and rebuilt cleanly
ALL_IDS = [
    "d1a5a3b4ba2e456cae989c756a622f1a",
    "34d74c3b001b4e6ba11cc9bebe829c38",
    "95477da53b314145a52a8b7cc656c460",
    "8173a3cdb3384350994db7edeebf49c7",
    "c1a32015c98c41859b74e4c9caae26e9",
    "70a811961eb340d5b1472a9f1aec7ad6",
    "a33f95a6830a41a2910c3eab917bbf69",
    "b09890afbfc04469be2a7c49b75fea06",
    "c5c9c603addd4b3e8129719a07f341e8",
    "cdb0a32fab854c9e8c3c6688b99339ae",
    "8a703c7a15a44cfeb6fe611f601f772a",
    "6a9d140ec220434497f96c7c3d6a6dc5",
    "27b41236379e42aba28020e6e00c33f4",
    "4bf4b3753bce4f9eb2217609f9e4657f",
    "6b8cdb81e7cc41a890243584a740bf61",
    "e0e0e3c039964c738724af056ddce41c",
    "5af4c64e501e4128844b3084cb05f3e3",
    "7e551eaeae514845805eff3bb718334d",
    "11d60e3eef2f45e6b2222e73966ce9a2",
    "127f9f24f4a846d6a159564d04bba361",
    "d2e34733027445b4894ac572b2cf626b",
    "316554b14a8240579ae1c3c47dd9078e",
    "e4a588ea270349f1aaff2922cb204dca",
    "b51dc5509aad416e8cbe7f99bb60e67e",
    "fddeb2d2dcad4a5caf3f47bc743bcb24",
    "934eba101cd74b08b5f5145d5a8840a4",
    "d602b442e6ad42d5aa979c2554f4aae4",
    "016c595847df40ea8d1e279ec3bef47c",
    "f59a450cba1d4febb0c174b85c6836b3",
    "d114068be6c64837ad8ab075424a8968",
    "42ee3f7a461a49dda829ea1719bd6b41",
    "d81cb430df6a41a5bbb0dec6092f31c4",
    "0a13c3422ced491a9f09d859caca6213",
    "93285d7626d34dfab5db29a9c07f9852",
    "112bc79bc95440379309f16908a06e07",
    "570cf92bed854b83891e1f2511628a70",
    "16bff7f295ed4ede85f5707771923f27",
    "3afc1dda8dd2436e9c79733008b4ba80",
    "763ef18957124a67ae9dd80fa5b1b11f",
    "cf04b89bcf414e11b8562531e30f54a9",
    "8b9db9cb562d494f91c4952c6410c662",
    "491a25c08011446e8f58a01345d31cd0",
    "8faacb434651424cb128da35c3171268",
    "00cfb2a8073d49c3a51a39dd960e18dc",
    "663a5a879e1d4f2dba571a5d8ceb65a1",
    "17f186764e51463c8227ceb56918f3cb",
    "5a5e49a5c6654d43a507b195f1de4a6c",
    "8b02f0f5e82d4a5ab857a7eb7e88d335",
]

# Manual adds — keep name exactly, no quantity
KEEP_AS_IS = [
    "Pipe Cleaners",
    "Chocolate covered almonds",
    "Cat Food",
    "Bananas",
    "Nature Valley Sweet and Salty Bars",
    "Matcha",
    "Whole milk",
    "Baby Broccoli",
    "Red lentils",
    "Beef Sticks from Costco",
]

# Recipe noise — delete with no replacement
# (optional avocado note, water, salt and pepper)

# Recipe-instruction-format items for Haiku to parse
NEEDS_CLEANING = [
    "2 cups sliced mushrooms",
    "2 cups fresh or frozen corn",
    "15 ounce can reduced sodium black beans, rinsed and drained",
    "2 boneless skinless chicken breasts halved lengthwise, 16 oz",
    "1/2 teaspoon adobo seasoning, or salt to taste",
    "3/4 teaspoon ground cumin",
    "1/4 teaspoon garlic powder",
    "1 1/4 cups chunky mild salsa",
    "1 cup shredded cheddar, reduced fat Sargento",
    "chopped cilantro for garnish",
    "3 to 4 pounds corned beef brisket uncooked, with spice packet",
    "1 onion",
    "3 cloves garlic sliced",
    "2 bay leaves",
    "2 pounds potatoes peeled & quartered",
    "2 large carrots chopped",
    "1 large head green cabbage cut into wedges",
    "4 bone in pork chops about 3 pounds",
    "1/2 teaspoon paprika",
    "1/2 teaspoon garlic powder",
    "1 tablespoon olive oil",
    "10.5 ounces condensed cream of mushroom soup 1 can",
    "10.5 ounces condensed cream of chicken soup 1 can",
    "3/4 cup reduced sodium beef broth",
    "1 small onion sliced",
    "20 oz. Diced Boneless Skinless Chicken Breasts",
    "2 Zucchini",
    "8 oz. Grape Tomatoes",
    "8 oz. Orzo Pasta",
    "4 oz. Tzatziki Dip",
    "1 oz. Crumbled Feta Cheese",
    "4 tsp. Chicken Broth Concentrate",
    "3/4 oz. Roasted Garlic & Herb Butter",
    "1.5 tsp. Garlic Salt",
    "2 tsp. Chimichurri Seasoning",
]

raw_list = "\n".join(f"{i+1}. {item}" for i, item in enumerate(NEEDS_CLEANING))

print("Calling Haiku to parse items...", file=sys.stderr)

response = client.messages.create(
    model="claude-haiku-4-5-20251001",
    max_tokens=2048,
    messages=[{
        "role": "user",
        "content": f"""You are a grocery list parser. Convert each raw ingredient into a clean grocery item.

Rules:
- name: clean store product name, Title Case, no cooking instructions (no "sliced", "chopped", "for garnish", "or salt to taste", "uncooked", "halved lengthwise", etc.)
- quantity: shopper-friendly amount string (e.g. "2 lbs", "1 can", "3 cloves", "¾ cup") — null if not applicable
- Merge duplicates that refer to the same ingredient into one item, summing quantities where the units match:
    - "1/4 tsp garlic powder" + "1/2 tsp garlic powder" → name: "Garlic Powder", quantity: "¾ tsp"
    - "1 onion" + "1 small onion sliced" → name: "Onion", quantity: "2"
    - "2 boneless skinless chicken breasts (16 oz)" + "20 oz diced boneless skinless chicken breasts" → name: "Boneless Skinless Chicken Breasts", quantity: "36 oz"
- Use unicode fractions (½ ¼ ¾) instead of 1/2, 1/4, 3/4
- Return a JSON array only, no markdown fences. Each element: {{"name": "...", "quantity": "..." or null}}

Items to parse:
{raw_list}"""
    }]
)

raw_json = response.content[0].text.strip()
if raw_json.startswith("```"):
    raw_json = "\n".join(raw_json.split("\n")[1:-1])

parsed = json.loads(raw_json)
print(f"Haiku returned {len(parsed)} items after merging", file=sys.stderr)

add_items = []

for name in KEEP_AS_IS:
    add_items.append({"name": name, "quantity": None, "details": None})

for item in parsed:
    add_items.append({
        "name": item["name"],
        "quantity": item.get("quantity"),
        "details": None,
    })

plan = {
    "delete_ids": ALL_IDS,
    "add_items": add_items,
    "list_name": "My Grocery List",
}

print(json.dumps(plan))
