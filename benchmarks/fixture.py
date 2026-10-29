"""Synthetic but executable multi-component application. No sleeps or mocked test outcomes."""
import json
from pathlib import Path
import subprocess

FILES = {
    '.gitignore': '.rbv/\n__pycache__/\n*.pyc\n',
    'src/__init__.py': '',
    'src/shared.py': 'def total(values):\n    return sum(values)\n',
    'src/pricing.py': 'from .shared import total\ndef price(values):\n    return total(values) * 9 // 10\n',
    'src/cart.py': 'from .pricing import price\ndef checkout(values):\n    return price(values) + 5\n',
    'src/access.py': 'def allowed(actor, owner):\n    return actor["tenant"] == owner["tenant"] and actor["role"] == "admin"\n',
    'src/storage.py': '''import sqlite3
def transfer(balance, amount):
    db = sqlite3.connect(":memory:")
    try:
        db.execute("CREATE TABLE accounts (id INTEGER PRIMARY KEY, balance INTEGER)")
        db.executemany("INSERT INTO accounts VALUES (?, ?)", [(1, balance), (2, 0)])
        db.commit()
        try:
            with db:
                db.execute("UPDATE accounts SET balance = balance - ? WHERE id = 1", (amount,))
                if amount > balance:
                    raise ValueError("insufficient funds")
                db.execute("UPDATE accounts SET balance = balance + ? WHERE id = 2", (amount,))
        except ValueError:
            pass
        return [r[0] for r in db.execute("SELECT balance FROM accounts ORDER BY id")]
    finally:
        db.close()
''',
    'src/search.py': 'def find(query, items):\n    return [v for v in items if query.casefold() in v.casefold()]\n',
    'src/loader.py': 'import json\ndef enabled(raw):\n    return json.loads(raw)["enabled"] is True\n',
    'docs/guide.md': '# Application guide\n',
    'checks.py': '''import json
import sys
from src import pricing, cart, access, storage, search, loader
name = sys.argv[1]
cases = int(sys.argv[2])
assertions = 0
for i in range(cases):
    values = [i % 101, i % 13, 10]
    expected = sum(values) * 9 // 10
    if name == "pricing":
        assert pricing.price(values) == expected
        assertions += 1
    elif name == "cart":
        assert cart.checkout(values) == expected + 5
        assertions += 1
    elif name == "security":
        assert not access.allowed({"tenant": i, "role": "admin"}, {"tenant": i + 1})
        assert access.allowed({"tenant": i, "role": "admin"}, {"tenant": i})
        assert not access.allowed({"tenant": i, "role": "reader"}, {"tenant": i})
        assertions += 3
    elif name == "data":
        assert storage.transfer(i + 1, i + 2) == [i + 1, 0]
        assert storage.transfer(i + 1, i) == [1, i]
        assertions += 2
    elif name == "search":
        items = [f"Item {i}", "STRASSE", "unrelated"]
        assert search.find("straße", items) == ["STRASSE"]
        assertions += 1
    elif name == "loader":
        assert not loader.enabled('{"enabled":"false"}')
        assert loader.enabled('{"enabled":true}')
        assertions += 2
    else:
        raise ValueError(name)
print(json.dumps({"group": name, "assertions": assertions}))
''',
}


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), '-c', 'core.autocrlf=false', *args],
                          capture_output=True, check=True).stdout.decode().strip()


def create(root, cases=1000):
    cfg = {
        'version': 1, 'impact_reviewed': True, 'docs': ['docs/*.md'], 'global': ['checks.py'],
        'components': {
            'shared': {'paths': ['src/shared.py']},
            'pricing': {'paths': ['src/pricing.py'], 'depends_on': ['shared']},
            'cart': {'paths': ['src/cart.py'], 'depends_on': ['pricing']},
            'access': {'paths': ['src/access.py']},
            'storage': {'paths': ['src/storage.py']},
            'search': {'paths': ['src/search.py']},
        },
        'protected': [
            {'name': 'tenant isolation', 'paths': ['src/access.py'], 'required_tags': ['security']},
            {'name': 'atomic balances', 'paths': ['src/storage.py'], 'required_tags': ['data']},
        ],
        'tests': [
            {'id': name, 'command': ['{python}', 'checks.py', name, str(cases)],
             'components': components, 'inputs': ['checks.py'], 'tags': tags,
             'cost': cost, 'cache': True}
            for name, components, tags, cost in [
                ('pricing', ['pricing', 'shared'], [], 1), ('cart', ['cart'], [], 1),
                ('security', ['access'], ['security'], 2), ('data', ['storage'], ['data'], 5),
                ('search', ['search'], [], 1), ('loader', [], [], 1),
            ]],
    }
    for name, value in FILES.items():
        p = root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(value, encoding='utf-8')
    (root / '.rbv.json').write_text(json.dumps(cfg), encoding='utf-8')
    git(root, 'init', '-q')
    git(root, 'add', '.')
    git(root, '-c', 'user.name=RBV Benchmark', '-c', 'user.email=benchmark@example.invalid',
        '-c', 'core.hooksPath=', 'commit', '-qm', 'baseline fixture')
    return cfg
