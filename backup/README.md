# Backups

Point-in-time copies of the wallpaper index, kept in the repo so the index can
never be lost even if the working tree is wiped again.

- `wallpapers-YYYY-MM-DD.json` - the full index: every category, every entry,
  every URL, the tag map and the version number.
- `manifest-YYYY-MM-DD.txt` - one line per image file: path, category, id.
  Use it to check a restore is complete.

The images themselves are not copied here; they live in the category folders and
in git history. This folder protects the index, which is the part that cannot be
rebuilt.

To restore from a snapshot: take the JSON, check every path in it exists in the
repo, drop any entry whose file is missing, then rebuild the `tags` map from the
surviving entries.
