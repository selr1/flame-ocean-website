# Test Fixtures Setup

This directory contains integration tests that require real firmware files and Python-generated reference files.

## Quick Start

### One-time Setup

Run the setup script to download and prepare all test fixtures:

```bash
bun run test:setup
```

This will:
1. Download all 16 ECHO MINI firmware versions (~500MB total)
2. Extract them to `/tmp/echo-mini-firmwares/`
3. Copy firmware files to `references/firmwares/` for Python processing
4. Run the Python extractor to generate reference BMP files
5. Create test fixtures at `/tmp/echo-mini-firmwares/extracted_bitmaps_smart/batch_auto/`

### Run Tests

After setup, run the integration tests:

```bash
bun test src/lib/rse/__tests__/python-extraction-integration.test.ts
```

Or use the npm script:

```bash
bun run test:integration
```

## Directory Structure

```
/tmp/echo-mini-firmwares/
├── ECHO MINI V1.2.5/
│   └── HIFIEC80.IMG           # Raw firmware file
├── ECHO MINI V1.8.0/
│   └── HIFIEC80.IMG
├── ...
└── extracted_bitmaps_smart/
    ├── batch_20260207_123456/  # Timestamped Python output
    │   ├── ECHO MINI V1.2.5/
    │   │   ├── IMAGE1.BMP      # Python-extracted reference
    │   │   └── ...
    │   └── ECHO MINI V1.8.0/
    │       ├── IMAGE1.BMP
    │       └── ...
    └── batch_auto/             # Stable symlinks to latest batch
        ├── ECHO MINI V1.2.5/
        └── ECHO MINI V1.8.0/
```

## File Locations

The test currently uses:
- **Firmware**: `/tmp/echo-mini-firmwares/ECHO MINI V1.8.0/HIFIEC80.IMG`
- **Python references**: `/tmp/echo-mini-firmwares/extracted_bitmaps_smart/batch_auto/ECHO MINI V1.8.0/`

## Why This Approach

1. **Self-contained tests** - No manual download required
2. **Consistent environment** - Same files across all machines
3. **Fast** - Tests only one version (V1.8.0), not all 16
4. **Reproducible** - Anyone can run tests with `bun run test:setup && bun test`

## Manual Setup (Alternative)

If you already have firmware files, you can also use them by:

1. Place your firmware files in `/tmp/echo-mini-firmwares/` in the structure:
   ```
   /tmp/echo-mini-firmwares/
   └── ECHO MINI V1.8.0/
       └── HIFIEC80.IMG
   ```

2. Run the Python extractor manually:
   ```bash
   # Copy firmware to references directory
   mkdir -p references/firmwares/ECHO\ MINI\ V1.8.0
   cp /tmp/echo-mini-firmwares/ECHO\ MINI\ V1.8.0/HIFIEC80.IMG references/firmwares/ECHO\ MINI\ V1.8.0/

   # Run Python extractor
   cd references
   python3 extract_resource_smart.py
   ```

3. Copy the output to the expected location:
   ```bash
   cp -r references/extracted_bitmaps_smart/batch_* /tmp/echo-mini-firmwares/extracted_bitmaps_smart/
   ```

Or update the constants in `python-extraction-integration.test.ts`:
```typescript
const FIRMWARE_PATH = '/path/to/your/HIFIEC80.IMG';
const PYTHON_EXTRACTED_PATH = '/path/to/python/extracted/files';
```

## Troubleshooting

### Python script not found

The setup script calls `python3 references/extract_resource_smart.py`. If you get an error:

```bash
# Make sure Python 3 is installed
python3 --version

# Make sure the script exists
ls references/extract_resource_smart.py
```

### curl not found

If `curl` is not available, install it:
```bash
# Ubuntu/Debian
sudo apt-get install curl

# macOS
# curl should be installed by default

# Or use wget instead (modify setup-fixtures.ts to use wget)
```

### unzip not found

If `unzip` is not available, install it:
```bash
# Ubuntu/Debian
sudo apt-get install unzip

# macOS
# unzip should be installed by default
```

### Disk space

The setup requires ~1GB of free space:
- ~500MB for firmware ZIP files
- ~500MB for extracted firmwares
- ~50MB for Python reference BMP files

### Permission denied when creating symlinks

If the setup script fails with permission errors creating symlinks, you can manually copy the files instead:

```bash
# Find the latest batch directory
ls /tmp/echo-mini-firmwares/extracted_bitmaps_smart/

# Copy it to batch_auto
cp -r /tmp/echo-mini-firmwares/extracted_bitmaps_smart/batch_<timestamp> \
      /tmp/echo-mini-firmwares/extracted_bitmaps_smart/batch_auto
```

## Cleanup

To free up disk space after testing:

```bash
# Remove all test fixtures
rm -rf /tmp/echo-mini-firmwares

# Remove Python working directory
rm -rf references/firmwares references/extracted_bitmaps_smart
```

## Advanced Options

### Skip downloading firmware

If you already have firmware files downloaded:

```bash
bun run test:setup --skip-download
```

### Skip Python extraction

If you already have Python reference files generated:

```bash
bun run test:setup --skip-python
```

### Test with different firmware version

Edit `python-extraction-integration.test.ts`:

```typescript
const TEST_VERSION = 'ECHO MINI V3.1.0';  // Change from V1.8.0
```

Then run setup and tests again.
