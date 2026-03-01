"""Sort and organize the Obsidian Realmforge vault."""
import os
import shutil

vault = r"C:\Users\issda\OneDrive\Dropbox\Izack Realmforge"

def ensure_dir(name):
    p = os.path.join(vault, name)
    os.makedirs(p, exist_ok=True)
    return p

def move_file(src_name, dest_folder, dest_name=None):
    src = os.path.join(vault, src_name)
    if os.path.exists(src):
        dst = os.path.join(vault, dest_folder, dest_name or os.path.basename(src_name))
        shutil.move(src, dst)
        print(f"  Moved: {src_name} -> {dest_folder}/")
        return True
    return False

# 1. Create organized folders
for d in ["Story Files", "ChatGPT Exports", "Lore", "Research Papers"]:
    ensure_dir(d)
    print(f"  Ensured: {d}/")

# 2. Move story/book TXT files
story_files = [
    "AVALON_BOOK_OUTLINE_FULL 1.txt",
    "AVALON_BOOK_OUTLINE_FULL.txt",
    "Based on all the research and your.txt",
    "Book things.txt",
    "Izack_Master_Lore_Archive23.txt",
    "# Epic Fantasy Mastery Transforming.txt",
    "# Positioning The Avalon Codex for.txt",
    "exposition.txt",
]
for f in story_files:
    move_file(f, "Story Files")

# Move any remaining TXT with book-related names
for f in os.listdir(vault):
    fp = os.path.join(vault, f)
    if os.path.isfile(fp) and f.endswith(".txt") and any(k in f for k in ["BOOK", "Spiral", "Avalon"]):
        shutil.move(fp, os.path.join(vault, "Story Files", f))
        print(f"  Moved: {f} -> Story Files/")

# 3. Move ChatGPT exports
for f in os.listdir(vault):
    if f.startswith("ChatGPT Data Export") and f.endswith(".html"):
        shutil.move(os.path.join(vault, f), os.path.join(vault, "ChatGPT Exports", f))
        print(f"  Moved: {f} -> ChatGPT Exports/")

# 4. Move PDFs
move_file("500 page doc on theroy.pdf", "Research Papers")
move_file("Thalorion_Ultimate_Campaign_Compendium.pdf", "Research Papers")
move_file("everweave-export.pdf", "Story Files")

# 5. Consolidate "Story Files etc/" into "Story Files/"
story_etc = os.path.join(vault, "Story Files etc")
if os.path.isdir(story_etc):
    for f in os.listdir(story_etc):
        src = os.path.join(story_etc, f)
        if os.path.isfile(src):
            shutil.move(src, os.path.join(vault, "Story Files", f))
            print(f"  Consolidated: Story Files etc/{f} -> Story Files/")
    if not os.listdir(story_etc):
        os.rmdir(story_etc)
        print("  Removed empty: Story Files etc/")

# 6. Move Untitled/ contents
untitled = os.path.join(vault, "Untitled")
if os.path.isdir(untitled):
    for f in os.listdir(untitled):
        src = os.path.join(untitled, f)
        if os.path.isfile(src):
            shutil.move(src, os.path.join(vault, "ChatGPT Exports", f))
            print(f"  Moved: Untitled/{f} -> ChatGPT Exports/")
    if not os.listdir(untitled):
        os.rmdir(untitled)
        print("  Removed empty: Untitled/")

# Untitled 1 -> Lore
untitled1 = os.path.join(vault, "Untitled 1")
if os.path.isdir(untitled1):
    for f in os.listdir(untitled1):
        src = os.path.join(untitled1, f)
        if os.path.isfile(src):
            shutil.move(src, os.path.join(vault, "Lore", f))
            print(f"  Moved: Untitled 1/{f} -> Lore/")
    if not os.listdir(untitled1):
        os.rmdir(untitled1)
        print("  Removed empty: Untitled 1/")

# Untitled 2 (empty)
untitled2 = os.path.join(vault, "Untitled 2")
if os.path.isdir(untitled2) and not os.listdir(untitled2):
    os.rmdir(untitled2)
    print("  Removed empty: Untitled 2/")

# 7. Consolidate "avalon files/" into "Story Files/"
avalon = os.path.join(vault, "avalon files")
if os.path.isdir(avalon):
    for f in os.listdir(avalon):
        src = os.path.join(avalon, f)
        if os.path.isfile(src):
            shutil.move(src, os.path.join(vault, "Story Files", f))
            print(f"  Consolidated: avalon files/{f} -> Story Files/")
    if not os.listdir(avalon):
        os.rmdir(avalon)
        print("  Removed empty: avalon files/")

# 8. Move AWS lambda pass
move_file("AWS labda Pass.md", "SCBE Architecture", "AWS Lambda Pass.md")

# 9. Move Untitled.md (orphan)
move_file("Untitled.md", "ChatGPT Exports", "Untitled Note.md")

# 10. Check VHDX
vhdx = os.path.join(vault, "REalmForge.vhdx")
if os.path.exists(vhdx):
    size_gb = os.path.getsize(vhdx) / (1024**3)
    print(f"\n  WARNING: REalmForge.vhdx ({size_gb:.2f} GB) in vault root")
    print(f"  This is a virtual disk. Consider moving outside vault.")

# 11. Final listing
print("\n=== FINAL VAULT STRUCTURE ===")
for item in sorted(os.listdir(vault)):
    full = os.path.join(vault, item)
    if os.path.isdir(full):
        count = len(os.listdir(full))
        print(f"  [DIR]  {item}/ ({count} items)")
    else:
        size_kb = os.path.getsize(full) / 1024
        print(f"  [FILE] {item} ({size_kb:.0f} KB)")
