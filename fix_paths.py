import os
import re
from pathlib import Path

LAB = Path(r"C:\Users\user\PycharmProjects\ContainerizationAndOrchestration\lab1")
SCREENS = LAB / "screenshots"
README = LAB / "README.md"

# 1. Собираем все png и сортируем по timestamp из имени
pattern = re.compile(r"Pasted image (\d+)\.png$")
files = []
for f in SCREENS.iterdir():
    m = pattern.match(f.name)
    if m:
        files.append((int(m.group(1)), f))

files.sort(key=lambda x: x[0])
print(f"Найдено файлов: {len(files)}")

# 2. Формируем mapping: старое имя -> новое имя
mapping = {}
for i, (_, old_path) in enumerate(files, start=1):
    new_name = f"{i:02d}.png"  # 01.png, 02.png, ...
    mapping[old_path.name] = new_name

# 3. Переименовываем файлы (через временное имя, чтобы не пересекались)
tmp_suffix = ".tmp_rename"
for old_name, new_name in mapping.items():
    old_path = SCREENS / old_name
    tmp_path = SCREENS / (old_name + tmp_suffix)
    old_path.rename(tmp_path)

for old_name, new_name in mapping.items():
    tmp_path = SCREENS / (old_name + tmp_suffix)
    final_path = SCREENS / new_name
    tmp_path.rename(final_path)
    print(f"  {old_name} -> {new_name}")

# 4. Переписываем README
text = README.read_text(encoding="utf-8")

# Заменяем все вхождения: ![alt](<screenshots/Pasted image X.png>)
# и ![alt](screenshots/Pasted image X.png) — оба варианта
def replace_link(match):
    alt = match.group("alt")
    fname = match.group("fname")
    new_name = mapping.get(fname)
    if new_name is None:
        print(f"  WARNING: {fname} not found in mapping")
        return match.group(0)
    return f"![{alt}](screenshots/{new_name})"

# паттерн: ![...](<screenshots/Pasted image ... .png>) или без <>
pattern_link = re.compile(
    r"!\[(?P<alt>[^\]]*)\]\(<?screenshots/(?P<fname>Pasted image \d+\.png)>?\)"
)

text = pattern_link.sub(replace_link, text)

README.write_text(text, encoding="utf-8")
print("\nREADME.md обновлён.")