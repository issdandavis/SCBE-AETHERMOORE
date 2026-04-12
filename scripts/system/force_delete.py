"""Force-delete a directory, handling Windows reserved names (nul, con, etc)."""
import os, sys, ctypes

target = sys.argv[1] if len(sys.argv) > 1 else r"C:\Users\issda\Dropbox (Old)"


def long(p):
    """Prefix with \\\\?\\ for extended-length path support."""
    a = os.path.abspath(p)
    if not a.startswith("\\\\?\\"):
        return "\\\\?\\" + a
    return a


def force_unlink(p):
    lp = long(p)
    try:
        os.unlink(lp)
    except PermissionError:
        # Try setting attributes to normal first
        ctypes.windll.kernel32.SetFileAttributesW(lp, 0x80)  # FILE_ATTRIBUTE_NORMAL
        os.unlink(lp)


def force_rmdir(p):
    lp = long(p)
    try:
        os.rmdir(lp)
    except PermissionError:
        ctypes.windll.kernel32.SetFileAttributesW(lp, 0x80)
        os.rmdir(lp)


def nuke(directory):
    skipped = []
    ldir = long(directory)
    for root, dirs, files in os.walk(ldir, topdown=False):
        for f in files:
            fp = os.path.join(root, f)
            try:
                force_unlink(fp)
            except Exception as e:
                skipped.append((fp, str(e)))
        for d in dirs:
            dp = os.path.join(root, d)
            try:
                force_rmdir(dp)
            except Exception as e:
                skipped.append((dp, str(e)))
    try:
        force_rmdir(ldir)
    except Exception as e:
        skipped.append((ldir, str(e)))

    if skipped:
        print(f"Skipped {len(skipped)} items:")
        for p, e in skipped[:10]:
            print(f"  {p}: {e}")
    else:
        print(f"Deleted: {directory}")


nuke(target)
