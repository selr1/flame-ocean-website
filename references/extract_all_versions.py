#!/usr/bin/env python3
"""
Batch Font Extractor - Process All Firmware Versions

This script orchestrates font extraction across all available firmware versions.
It scans for firmware files and executes the universal font extractor with
comprehensive Unicode range coverage.

Features:
- Automatic discovery of firmware files in nested directory structures
- Batch processing of all versions with timeout protection
- Organized output by firmware version and Unicode planes
- Progress tracking and statistical reporting

Output Organization:
    extracted_font_all_versions/
    ├── <version>/
    │   ├── SMALL/
    │   │   ├── Basic_Latin/
    │   │   ├── CJK_Unified/
    │   │   └── ...
    │   └── LARGE/
    │       ├── Basic_Latin/
    │       ├── CJK_Unified/
    │       └── ...
"""

import sys
import glob
import subprocess
import os

OUTPUT_BASE = 'extracted_font_all_versions'

# Comprehensive Unicode range definitions covering all major scripts and symbols
UNICODE_RANGES = [
    ("Basic_Latin", 0x0000, 0x007F),
    ("Latin_1_Supplement", 0x0080, 0x00FF),
    ("Latin_Extended_A", 0x0100, 0x017F),
    ("Latin_Extended_B", 0x0180, 0x024F),
    ("IPA_Extensions", 0x0250, 0x02AF),
    ("Spacing_Modifier", 0x02B0, 0x02FF),
    ("Combining_Diacritics", 0x0300, 0x036F),
    ("Greek_Coptic", 0x0370, 0x03FF),
    ("Cyrillic", 0x0400, 0x04FF),
    ("Cyrillic_Supplement", 0x0500, 0x052F),
    ("Armenian", 0x0530, 0x058F),
    ("Hebrew", 0x0590, 0x05FF),
    ("Arabic", 0x0600, 0x06FF),
    ("Syriac", 0x0700, 0x074F),
    ("Arabic_Supplement", 0x0750, 0x077F),
    ("Thaana", 0x0780, 0x07BF),
    ("NKo", 0x07C0, 0x07FF),
    ("Samaritan", 0x0800, 0x083F),
    ("Mandaic", 0x0840, 0x085F),
    ("Arabic_Extended_B", 0x0870, 0x089F),
    ("Arabic_Extended_A", 0x08A0, 0x08FF),
    ("Devanagari", 0x0900, 0x097F),
    ("Bengali", 0x0980, 0x09FF),
    ("Gurmukhi", 0x0A00, 0x0A7F),
    ("Gujarati", 0x0A80, 0x0AFF),
    ("Oriya", 0x0B00, 0x0B7F),
    ("Tamil", 0x0B80, 0x0BFF),
    ("Telugu", 0x0C00, 0x0C7F),
    ("Kannada", 0x0C80, 0x0CFF),
    ("Malayalam", 0x0D00, 0x0D7F),
    ("Sinhala", 0x0D80, 0x0DFF),
    ("Thai", 0x0E00, 0x0E7F),
    ("Lao", 0x0E80, 0x0EFF),
    ("Tibetan", 0x0F00, 0x0FFF),
    ("Myanmar", 0x1000, 0x109F),
    ("Georgian", 0x10A0, 0x10FF),
    ("Hangul_Jamo", 0x1100, 0x11FF),
    ("Ethiopic", 0x1200, 0x137F),
    ("Ethiopic_Supplement", 0x1380, 0x139F),
    ("Cherokee", 0x13A0, 0x13FF),
    ("UCAS", 0x1400, 0x167F),
    ("Ogham", 0x1680, 0x169F),
    ("Runic", 0x16A0, 0x16FF),
    ("Tagalog", 0x1700, 0x171F),
    ("Hanunoo", 0x1720, 0x173F),
    ("Buhid", 0x1740, 0x175F),
    ("Tagbanwa", 0x1760, 0x177F),
    ("Khmer", 0x1780, 0x17FF),
    ("Mongolian", 0x1800, 0x18AF),
    ("UCAS_Extended", 0x18B0, 0x18FF),
    ("Limbu", 0x1900, 0x194F),
    ("Tai_Le", 0x1950, 0x197F),
    ("New_Tai_Lue", 0x1980, 0x19DF),
    ("Khmer_Symbols", 0x19E0, 0x19FF),
    ("Buginese", 0x1A00, 0x1A1F),
    ("Tai_Tham", 0x1A20, 0x1AAF),
    ("Balinese", 0x1B00, 0x1B7F),
    ("Sundanese", 0x1B80, 0x1BBF),
    ("Batak", 0x1BC0, 0x1BFF),
    ("Lepcha", 0x1C00, 0x1C4F),
    ("Ol_Chiki", 0x1C50, 0x1C7F),
    ("Cyrillic_Extended_C", 0x1C80, 0x1C8F),
    ("Georgian_Extended", 0x1C90, 0x1CBF),
    ("Vedic_Extensions", 0x1CD0, 0x1CFF),
    ("Phonetic_Extensions", 0x1D00, 0x1D7F),
    ("Phonetic_Extensions_Sup", 0x1D80, 0x1DBF),
    ("Combining_Diacritics_Sup", 0x1DC0, 0x1DFF),
    ("Latin_Extended_Additional", 0x1E00, 0x1EFF),
    ("Greek_Extended", 0x1F00, 0x1FFF),
    ("General_Punctuation", 0x2000, 0x206F),
    ("Superscripts_Subscripts", 0x2070, 0x209F),
    ("Currency_Symbols", 0x20A0, 0x20CF),
    ("Combining_Diacritics_Sym", 0x20D0, 0x20FF),
    ("Letterlike_Symbols", 0x2100, 0x214F),
    ("Number_Forms", 0x2150, 0x218F),
    ("Arrows", 0x2190, 0x21FF),
    ("Mathematical_Operators", 0x2200, 0x22FF),
    ("Misc_Technical", 0x2300, 0x23FF),
    ("Control_Pictures", 0x2400, 0x243F),
    ("OCR", 0x2440, 0x245F),
    ("Enclosed_Alphanumerics", 0x2460, 0x24FF),
    ("Box_Drawing", 0x2500, 0x257F),
    ("Block_Elements", 0x2580, 0x259F),
    ("Geometric_Shapes", 0x25A0, 0x25FF),
    ("Misc_Symbols", 0x2600, 0x26FF),
    ("Dingbats", 0x2700, 0x27BF),
    ("Misc_Math_Symbols_A", 0x27C0, 0x27EF),
    ("Supplemental_Arrows_A", 0x27F0, 0x27FF),
    ("Braille_Patterns", 0x2800, 0x28FF),
    ("Supplemental_Arrows_B", 0x2900, 0x297F),
    ("Misc_Math_Symbols_B", 0x2980, 0x29FF),
    ("Supplemental_Math_Op", 0x2A00, 0x2AFF),
    ("Misc_Symbols_Arrows", 0x2B00, 0x2BFF),
    ("Glagolitic", 0x2C00, 0x2C5F),
    ("Latin_Extended_C", 0x2C60, 0x2C7F),
    ("Coptic", 0x2C80, 0x2CFF),
    ("Georgian_Supplement", 0x2D00, 0x2D2F),
    ("Tifinagh", 0x2D30, 0x2D7F),
    ("Ethiopic_Extended", 0x2D80, 0x2DDF),
    ("Cyrillic_Extended_A", 0x2DE0, 0x2DFF),
    ("Supplemental_Punctuation", 0x2E00, 0x2E7F),
    ("CJK_Radicals_Sup", 0x2E80, 0x2EFF),
    ("Kangxi_Radicals", 0x2F00, 0x2FDF),
    ("Ideographic_Description", 0x2FF0, 0x2FFF),
    ("CJK_Symbols_Punctuation", 0x3000, 0x303F),
    ("Hiragana", 0x3040, 0x309F),
    ("Katakana", 0x30A0, 0x30FF),
    ("Bopomofo", 0x3100, 0x312F),
    ("Hangul_Compatibility", 0x3130, 0x318F),
    ("Kanbun", 0x3190, 0x319F),
    ("Bopomofo_Extended", 0x31A0, 0x31BF),
    ("CJK_Strokes", 0x31C0, 0x31EF),
    ("Katakana_Phonetic", 0x31F0, 0x31FF),
    ("Enclosed_CJK", 0x3200, 0x32FF),
    ("CJK_Compatibility", 0x3300, 0x33FF),
    ("CJK_Extension_A", 0x3400, 0x4DBF),
    ("Yijing_Hexagrams", 0x4DC0, 0x4DFF),
    ("CJK_Unified", 0x4E00, 0x9FFF),
    ("Yi_Syllables", 0xA000, 0xA48F),
    ("Yi_Radicals", 0xA490, 0xA4CF),
    ("Lisu", 0xA4D0, 0xA4FF),
    ("Vai", 0xA500, 0xA63F),
    ("Cyrillic_Extended_B", 0xA640, 0xA69F),
    ("Bamum", 0xA6A0, 0xA6FF),
    ("Modifier_Tone_Letters", 0xA700, 0xA71F),
    ("Latin_Extended_D", 0xA720, 0xA7FF),
    ("Syloti_Nagri", 0xA800, 0xA82F),
    ("Indic_Number_Forms", 0xA830, 0xA83F),
    ("Phags_pa", 0xA840, 0xA87F),
    ("Saurashtra", 0xA880, 0xA8DF),
    ("Devanagari_Extended", 0xA8E0, 0xA8FF),
    ("Kayah_Li", 0xA900, 0xA92F),
    ("Rejang", 0xA930, 0xA95F),
    ("Hangul_Jamo_Extended_A", 0xA960, 0xA97F),
    ("Javanese", 0xA980, 0xA9DF),
    ("Myanmar_Extended_B", 0xA9E0, 0xA9FF),
    ("Cham", 0xAA00, 0xAA5F),
    ("Myanmar_Extended_A", 0xAA60, 0xAA7F),
    ("Tai_Viet", 0xAA80, 0xAADF),
    ("Meetei_Mayek_Ext", 0xAAE0, 0xAAFF),
    ("Ethiopic_Extended_A", 0xAB00, 0xAB2F),
    ("Latin_Extended_E", 0xAB30, 0xAB6F),
    ("Cherokee_Supplement", 0xAB70, 0xABBF),
    ("Meetei_Mayek", 0xABC0, 0xABFF),
    ("Hangul_Syllables", 0xAC00, 0xD7AF),
    ("Hangul_Jamo_Extended_B", 0xD7B0, 0xD7FF),
    ("Private_Use_Area", 0xE000, 0xF8FF),
    ("CJK_Compatibility_Ideographs", 0xF900, 0xFAFF),
    ("Alphabetic_Presentation_Forms", 0xFB00, 0xFB4F),
    ("Arabic_Presentation_Forms_A", 0xFB50, 0xFDFF),
    ("Variation_Selectors", 0xFE00, 0xFE0F),
    ("Vertical_Forms", 0xFE10, 0xFE1F),
    ("Combining_Half_Marks", 0xFE20, 0xFE2F),
    ("CJK_Compatibility_Forms", 0xFE30, 0xFE4F),
    ("Small_Form_Variants", 0xFE50, 0xFE6F),
    ("Arabic_Presentation_Forms_B", 0xFE70, 0xFEFF),
    ("Halfwidth_Fullwidth", 0xFF00, 0xFFEF),
    ("Specials", 0xFFF0, 0xFFFF),
]

firmware_dirs = []
for path in glob.glob('firmwares/*/HIFIEC*.IMG'):
    dir_name = os.path.basename(os.path.dirname(path))
    firmware_dirs.append((dir_name, path))

for path in glob.glob('firmwares/*/*/HIFIEC*.IMG'):
    dir_name = os.path.basename(os.path.dirname(os.path.dirname(path)))
    firmware_dirs.append((dir_name, path))

firmware_dirs = sorted(set(firmware_dirs))

print("=" * 80)
print(f"Batch Font Extraction for All Versions")
print(f"Found {len(firmware_dirs)} firmware versions")
print("=" * 80)
print()

results = []

for version, fw_path in firmware_dirs:
    print(f"\nProcessing: {version}")
    print(f"  Firmware: {fw_path}")

    output_dir = os.path.join(OUTPUT_BASE, version)

    ranges_args = []
    for name, start, end in UNICODE_RANGES:
        ranges_args.extend([f"--range", f"{name}:{hex(start)}:{hex(end)}"])

    cmd = [
        sys.executable,
        'extract_font_universal.py',
        fw_path,
        '-o', output_dir,
        *ranges_args
    ]

    print(f"  Output: {output_dir}")
    print(f"  Command: {' '.join(cmd[:3])} ...")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            output_lines = result.stdout.split('\n')
            small_count = 0
            large_count = 0

            for line in output_lines:
                if 'SMALL:' in line and 'extracted' in line:
                    try:
                        small_count = int(line.split('SMALL:')[1].split('fonts')[0].strip())
                    except:
                        pass
                if 'LARGE:' in line and 'extracted' in line:
                    try:
                        large_count = int(line.split('LARGE:')[1].split('fonts')[0].strip())
                    except:
                        pass

            print(f"  ✅ Success: SMALL={small_count}, LARGE={large_count}")
            results.append({
                'version': version,
                'status': '✅',
                'small': small_count,
                'large': large_count
            })
        else:
            print(f"  ❌ Failed: {result.returncode}")
            print(f"  Error: {result.stderr[:200]}")
            results.append({
                'version': version,
                'status': '❌',
                'small': 0,
                'large': 0
            })

    except subprocess.TimeoutExpired:
        print(f"  ⏰ Timeout")
        results.append({
            'version': version,
            'status': '⏰',
            'small': 0,
            'large': 0
        })

print()
print("=" * 80)
print("Batch Extraction Complete")
print("=" * 80)
print()
print(f"{'Version':<25} {'Status':<5} {'SMALL':<10} {'LARGE':<10}")
print("-" * 60)

total_small = 0
total_large = 0
success_count = 0

for r in results:
    print(f"{r['version']:<25} {r['status']:<5} {r['small']:<10} {r['large']:<10}")
    total_small += r['small']
    total_large += r['large']
    if r['status'] == '✅':
        success_count += 1

print("-" * 60)
print(f"Total: {success_count}/{len(results)} successful")
print(f"Total extracted: SMALL={total_small}, LARGE={total_large}")
print(f"Output directory: {OUTPUT_BASE}/")
