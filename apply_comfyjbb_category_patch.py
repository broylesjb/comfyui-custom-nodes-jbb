from pathlib import Path
import re

repo = Path(".").resolve()
changed = []

for p in repo.rglob("*.py"):
    if ".git" in p.parts or "tests" in p.parts:
        continue

    txt = p.read_text(encoding="utf-8")
    new = txt

    # 1) CATEGORY = "COMFYJBB"
    new = re.sub(
        r'^(\s*CATEGORY\s*=\s*)(["\']).*?\2',
        r'\1"COMFYJBB"',
        new,
        flags=re.M
    )

    # 2) Prefix only NODE_DISPLAY_NAME_MAPPINGS values
    m = re.search(r'NODE_DISPLAY_NAME_MAPPINGS\s*=\s*\{', new)
    if m:
        start = m.end() - 1
        depth = 0
        end = None
        for i in range(start, len(new)):
            c = new[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = i
                    break

        if end is not None:
            block = new[start:end+1]

            def repl(mm):
                key = mm.group(1)
                val = mm.group(2)
                if val.startswith("COMFYJBB:"):
                    return mm.group(0)
                return f'"{key}": "COMFYJBB: {val}"'

            block2 = re.sub(r'"([^"]+)"\s*:\s*"([^"]+)"', repl, block)
            new = new[:start] + block2 + new[end+1:]

    if new != txt:
        p.write_text(new, encoding="utf-8")
        changed.append(str(p.relative_to(repo)))

print("Changed files:")
for c in changed:
    print("-", c)
