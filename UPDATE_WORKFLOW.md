# Complete Update Workflow

## Current script: `update_all.py`

`update_all.py` does everything in one run: it resizes new/changed source images, reads EXIF,
and updates the database.

```bash
python3 update_all.py --dry-run          # Show what would change; changes nothing
python3 update_all.py                    # Normal update
python3 update_all.py --prune            # Also delete orphaned images (see below)
python3 update_all.py --reload-marked    # Only re-process images marked "reload" in the gallery
python3 update_all.py --skip-processing  # Only re-read EXIF and update the database
python3 update_all.py --force            # Re-process every image
```

**Edited images / EXIF.** A source file is re-processed whenever its size or modification time
differs from the last run, so EXIF edits are picked up even by tools that keep the original
modification time (e.g. `exiftool -P`). EXIF is re-read from the library on every run.

**Renamed images or batches.** Each image's pixels are fingerprinted (`images.content_hash`,
added automatically on the first run; see `add_content_hash.sql`). When a source file or batch
folder is renamed, the existing database row is moved to the new name, so tags, descriptions and
favorites are kept and the old library copy is removed. Duplicates left behind by renames made
with older versions of the script are merged the same way. Old share links to the previous name
stop working.

**Orphans.** Images whose source file is gone (and that don't match a renamed file) are listed
at the end of every run, with any tags/description/favorites they have. They are only deleted
with `--prune`. As a safety net, `--prune` does nothing when a source directory is missing (e.g.
the NAS isn't mounted), ignores batches whose symlink can't be read, and refuses to delete more
than 10% of the library unless `--allow-mass-prune` is given. Run `--dry-run --prune` first.

Renames are recognised by identical pixels, so a file that was renamed *and* re-scanned or
re-edited at the same time shows up as a new image plus an orphan instead.
