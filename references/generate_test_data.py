#!/usr/bin/env python3
"""
Generate test data to verify TypeScript implementation produces identical output

This script generates comprehensive test data from the Python reference implementation
that can be used to verify the TypeScript version behaves identically.

Test Categories:
- Bitmap Conversion: RGB565 to BMP format conversion with various dimensions
- Font Decoding: V8 font data decoding with different configurations
- Misalignment Detection: Offset table misalignment detection algorithms

Output Format:
    JSON file containing input/output pairs for each test case, organized by category.
"""

import struct
import json
import sys
from pathlib import Path


# ============================================================================
# Bitmap Conversion Functions
# ============================================================================

def swap_bytes_16bit(data):
    """Swap odd and even bytes to convert between big-endian and little-endian.

    This function reverses byte pairs in the data, which is commonly needed when
    converting between different byte order representations of 16-bit values.

    Args:
        data: Input bytes to swap

    Returns:
        Bytes with odd/even positions swapped. If the input has odd length,
        the last byte is discarded.

    Example:
        >>> swap_bytes_16bit(b'\\x12\\x34\\x56\\x78')
        b'\\x34\\x12\\x78\\x56'
    """
    arr = bytearray(data)
    if len(arr) % 2 != 0:
        arr = arr[:-1]
    arr[0::2], arr[1::2] = arr[1::2], arr[0::2]
    return bytes(arr)


def get_stride_info(width):
    """Calculate stride and padding information for BMP row alignment.

    BMP files require each row to be aligned to 4-byte boundaries. This function
    calculates the source stride (compact data) and destination stride (BMP-aligned).

    Args:
        width: Image width in pixels

    Returns:
        Tuple of (source_stride, destination_stride, padding_bytes)
        - source_stride: Bytes per row in compact format (width * 2 for RGB565)
        - destination_stride: Bytes per row after 4-byte alignment
        - padding: Number of padding bytes added per row
    """
    src_stride = width * 2
    dst_stride = (src_stride + 3) & ~3
    padding = dst_stride - src_stride
    return src_stride, dst_stride, padding


def restride_to_bmp(raw_data, width, height):
    """Convert compact pixel data to BMP-aligned row format.

    Takes tightly-packed RGB565 data and inserts padding bytes at the end of
    each row to meet BMP's 4-byte alignment requirement.

    Args:
        raw_data: Compact pixel data (width * height * 2 bytes expected)
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        BMP-aligned pixel data with padding bytes inserted.
    """
    src_stride, dst_stride, padding = get_stride_info(width)

    if padding == 0 and len(raw_data) == src_stride * height:
        return raw_data

    expected_len = src_stride * height
    if len(raw_data) < expected_len:
        raw_data += b'\x00' * (expected_len - len(raw_data))

    output = bytearray()
    for y in range(height):
        src_start = y * src_stride
        src_end = src_start + src_stride
        output.extend(raw_data[src_start:src_end])
        if padding > 0:
            output.extend(b'\x00' * padding)

    return bytes(output)


def create_bmp_header(width, height):
    """Generate BMP file header for RGB565 format with bit masks.

    Creates a complete BMP header including file header, info header, and
    color channel masks for the RGB565 format (5 bits red, 6 bits green, 5 bits blue).

    Args:
        width: Image width in pixels
        height: Image height in pixels (stored as negative for top-down bitmap)

    Returns:
        Complete BMP header as bytes (14 byte file header + 40 byte info header + 12 byte masks)
    """
    src_stride, dst_stride, padding = get_stride_info(width)
    image_size = dst_stride * height
    headers_size = 14 + 40 + 12
    file_size = headers_size + image_size

    header = b'BM'
    header += struct.pack('<I', file_size)
    header += b'\x00\x00\x00\x00'
    header += struct.pack('<I', headers_size)
    header += struct.pack('<I', 40)
    header += struct.pack('<i', width)
    header += struct.pack('<i', -height)
    header += struct.pack('<H', 1)
    header += struct.pack('<H', 16)
    header += struct.pack('<I', 3)
    header += struct.pack('<I', image_size)
    header += struct.pack('<i', 2835)
    header += struct.pack('<i', 2835)
    header += struct.pack('<I', 0)
    header += struct.pack('<I', 0)
    header += struct.pack('<I', 0xF800)  # Red mask (5 bits)
    header += struct.pack('<I', 0x07E0)  # Green mask (6 bits)
    header += struct.pack('<I', 0x001F)  # Blue mask (5 bits)

    return header


def convert_to_bmp(raw_data, width, height):
    """Convert raw RGB565 pixel data to a valid BMP file.

    Performs the complete conversion pipeline:
    1. Byte swap (big-endian to little-endian)
    2. Row alignment (add padding for 4-byte boundaries)
    3. Header generation

    Args:
        raw_data: Raw RGB565 pixel data (2 bytes per pixel)
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        Complete BMP file as bytes, or None if dimensions are invalid.
    """
    if width <= 0 or height <= 0:
        return None

    expected_size = width * height * 2
    if len(raw_data) < expected_size:
        raw_data += b'\x00' * (expected_size - len(raw_data))

    pixel_data = swap_bytes_16bit(raw_data[:expected_size])
    pixel_data = restride_to_bmp(pixel_data, width, height)
    header = create_bmp_header(width, height)

    return header + pixel_data


# ============================================================================
# Font Decoding Functions
# ============================================================================

def decode_v8(chunk, lookup_val):
    """Decode V8 format font data into pixel rows.

    The V8 font format uses a variable encoding scheme controlled by flags
    in the lookup value. This function handles the various bit swapping and
    byte reordering configurations.

    Args:
        chunk: Raw font data bytes (16 bytes per character)
        lookup_val: Configuration value from lookup table containing decode flags

    Returns:
        List of pixel rows, where each row is a list of bits (0 or 1).
        Each character is 16 pixels wide by 16 pixels tall.

    Configuration Flags (from lookup_val & 0xFF):
        - bit 3 (sw_mcu_bits): Controls bit interpretation mode
        - bit 4 (sw_mcu_hw_swap): Controls hardware byte swapping
        - bit 5 (sw_mcu_byte_swap): Controls software byte swapping
    """
    config_byte = lookup_val & 0xFF
    sw_mcu_bits = (config_byte >> 3) & 1
    sw_mcu_hw_swap = (config_byte >> 4) & 1
    sw_mcu_byte_swap = (config_byte >> 5) & 1

    pixels = []
    for i in range(0, len(chunk), 2):
        if i + 1 >= len(chunk):
            break

        b0, b1 = chunk[i], chunk[i + 1]

        if sw_mcu_bits == 1:
            val = (b1 << 8) | b0
            if sw_mcu_byte_swap:
                val = ((val & 0xFF) << 8) | ((val >> 8) & 0xFF)
            final_pixel = val
        else:
            cycle_1, cycle_2 = (b1, b0) if sw_mcu_hw_swap == sw_mcu_byte_swap else (b0, b1)
            if sw_mcu_byte_swap:
                cycle_1, cycle_2 = cycle_2, cycle_1
            if sw_mcu_hw_swap:
                cycle_1, cycle_2 = cycle_2, cycle_1
            final_pixel = cycle_2 | (cycle_1 << 8)

        if not ((sw_mcu_bits == 1) and (sw_mcu_byte_swap == 1)):
            final_pixel = ((final_pixel & 0xFF) << 8) | ((final_pixel >> 8) & 0xFF)

        row_bits = [(final_pixel >> bit) & 1 for bit in range(15, 0, -1)]
        pixels.append(row_bits)

    return pixels


def write_bmp_header_only(width=15, height=16):
    """Generate monochrome BMP file header.

    Creates a BMP header for 1-bit per pixel monochrome images.
    Includes the file header, info header, and 2-color palette (black and white).

    Args:
        width: Image width in pixels (default: 15)
        height: Image height in pixels (default: 16)

    Returns:
        Complete BMP header as bytes (62 bytes total).
    """
    import struct as struct_pkg
    bfType = 0x4D42
    bfOffBits = 62
    biSize = 40
    biWidth = width
    biHeight = height
    biBitCount = 1
    biSizeImage = ((width + 31) // 32) * 4 * height

    file_size = bfOffBits + biSizeImage

    header = bytearray()
    header.extend(struct_pkg.pack('<H', bfType))
    header.extend(struct_pkg.pack('<I', file_size))
    header.extend(struct_pkg.pack('<H', 0))
    header.extend(struct_pkg.pack('<H', 0))
    header.extend(struct_pkg.pack('<I', bfOffBits))
    header.extend(struct_pkg.pack('<I', biSize))
    header.extend(struct_pkg.pack('<i', biWidth))
    header.extend(struct_pkg.pack('<i', biHeight))
    header.extend(struct_pkg.pack('<H', 1))
    header.extend(struct_pkg.pack('<H', biBitCount))
    header.extend(struct_pkg.pack('<I', 0))
    header.extend(struct_pkg.pack('<I', biSizeImage))
    header.extend(struct_pkg.pack('<i', 2835))
    header.extend(struct_pkg.pack('<i', 2835))
    header.extend(struct_pkg.pack('<I', 2))
    header.extend(struct_pkg.pack('<I', 2))

    for color in [0xFFFFFF, 0x000000]:
        header.extend(struct_pkg.pack('BBBB', color & 0xFF, (color >> 8) & 0xFF, (color >> 16) & 0xFF, 0))

    return bytes(header)


def encode_mono_bmp_pixels(pixels, width=15, height=16):
    """Encode pixel data to monochrome BMP format.

    Converts a 2D pixel array into the BMP monochrome format where each row
    is padded to 4-byte boundaries and stored bottom-up.

    Args:
        pixels: 2D list of bits (0 or 1), where pixels[y][x] is the pixel at column x, row y
        width: Image width in pixels (default: 15)
        height: Image height in pixels (default: 16)

    Returns:
        Encoded pixel data as bytes, ready to be written after the BMP header.
    """
    row_bytes = ((width + 31) // 32) * 4
    pixel_data = bytearray()

    for y in range(height - 1, -1, -1):
        row_data = []
        current_byte = 0
        bit_count = 0

        for x in range(width):
            bit = pixels[y][x] if y < len(pixels) and x < len(pixels[y]) else 0
            current_byte = (current_byte << 1) | bit
            bit_count += 1

            if bit_count == 8:
                row_data.append(current_byte)
                current_byte = 0
                bit_count = 0

        if bit_count > 0:
            current_byte <<= (8 - bit_count)
            row_data.append(current_byte)

        while len(row_data) < row_bytes:
            row_data.append(0)

        pixel_data.extend(row_data)

    return bytes(pixel_data)


# ============================================================================
# Test Data Generation Functions
# ============================================================================

def generate_bitmap_test_data():
    """Generate comprehensive test cases for bitmap conversion functions.

    Creates test data covering:
    - Basic RGB565 to BMP conversion with various sizes
    - Byte swapping operations
    - Stride calculation for different widths
    - Row alignment and padding
    - BMP header generation
    - Edge cases (invalid dimensions)

    Returns:
        Dictionary containing test cases under 'bitmap_conversion' key.
    """
    print("Generating bitmap conversion test data...")

    tests = []

    # Test 1: 2x2 RGB565 data
    raw_data = bytes([
        0xff, 0x00,  # red
        0x00, 0x07,  # blue
        0xe0, 0x07,  # green
        0xff, 0xf8   # white
    ])
    result = convert_to_bmp(raw_data, 2, 2)
    tests.append({
        'name': '2x2 RGB565 to BMP',
        'input': {
            'raw_data': list(raw_data),
            'width': 2,
            'height': 2
        },
        'output': {
            'bmp_data': list(result) if result else None,
            'first_bytes': list(result[:10]) if result else None
        }
    })

    # Test 2: 4x4 pattern
    raw_data = bytes([
        0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0,
        0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88,
        0x99, 0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x00,
        0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08
    ])
    result = convert_to_bmp(raw_data, 4, 4)
    tests.append({
        'name': '4x4 RGB565 to BMP',
        'input': {
            'raw_data': list(raw_data),
            'width': 4,
            'height': 4
        },
        'output': {
            'bmp_data': list(result) if result else None
        }
    })

    # Test 3: swap_bytes_16bit
    input_data = bytes([0x12, 0x34, 0x56, 0x78])
    swapped = swap_bytes_16bit(input_data)
    tests.append({
        'name': 'swap_bytes_16bit',
        'input': {
            'data': list(input_data)
        },
        'output': {
            'swapped': list(swapped)
        }
    })

    # Test 4: get_stride_info
    for width in [10, 15, 16, 17, 32, 33]:
        src, dst, pad = get_stride_info(width)
        tests.append({
            'name': f'get_stride_info width={width}',
            'input': {'width': width},
            'output': {
                'src_stride': src,
                'dst_stride': dst,
                'padding': pad
            }
        })

    # Test 5: restride_to_bmp
    raw_data = bytes([i & 0xFF for i in range(100)])  # 5x10 pixels (100 bytes)
    aligned = restride_to_bmp(raw_data, 5, 10)
    tests.append({
        'name': 'restride_to_bmp 5x10',
        'input': {
            'raw_data': list(raw_data),
            'width': 5,
            'height': 10
        },
        'output': {
            'aligned_data': list(aligned)
        }
    })

    # Test 6: create_bmp_header
    for width, height in [(15, 16), (100, 50)]:
        header = create_bmp_header(width, height)
        tests.append({
            'name': f'create_bmp_header {width}x{height}',
            'input': {'width': width, 'height': height},
            'output': {
                'header': list(header),
                'header_size': len(header)
            }
        })

    # Test 7: Invalid dimensions
    result = convert_to_bmp(bytes([1, 2, 3, 4]), 0, 10)
    tests.append({
        'name': 'convert_to_bmp invalid width=0',
        'input': {'raw_data': [1, 2, 3, 4], 'width': 0, 'height': 10},
        'output': {'result': result}
    })

    result = convert_to_bmp(bytes([1, 2, 3, 4]), -1, 10)
    tests.append({
        'name': 'convert_to_bmp invalid width=-1',
        'input': {'raw_data': [1, 2, 3, 4], 'width': -1, 'height': 10},
        'output': {'result': result}
    })

    return {'bitmap_conversion': tests}


def generate_font_test_data():
    """Generate comprehensive test cases for font decoding functions.

    Creates test data covering:
    - V8 font decoding with various lookup values (configuration flags)
    - Monochrome BMP header generation
    - Pixel encoding for common patterns (all white, checkerboard, single column)

    Returns:
        Dictionary containing test cases under 'font_decoding' key.
    """
    print("Generating font decoding test data...")

    tests = []

    # Test 1: decode_v8 with different lookup values
    # Create test chunk data
    chunk = bytes([i & 0xFF for i in range(32)])

    # Test various lookup values (different configurations)
    for lookup_val in [0x00, 0x08, 0x10, 0x18, 0x20, 0x28]:
        pixels = decode_v8(chunk, lookup_val)
        tests.append({
            'name': f'decode_v8 lookup=0x{lookup_val:02X}',
            'input': {
                'chunk': list(chunk),
                'lookup_val': lookup_val
            },
            'output': {
                'pixels': pixels  # List of lists of bits
            }
        })

    # Test 2: write_bmp_header_only
    for width, height in [(15, 16), (20, 20)]:
        header = write_bmp_header_only(width, height)
        tests.append({
            'name': f'write_bmp_header_only {width}x{height}',
            'input': {'width': width, 'height': height},
            'output': {
                'header': list(header),
                'header_size': len(header)
            }
        })

    # Test 3: encode_mono_bmp_pixels with known patterns
    # All white
    pixels_all_white = [[1 for _ in range(15)] for _ in range(16)]
    pixel_data = encode_mono_bmp_pixels(pixels_all_white, 15, 16)
    tests.append({
        'name': 'encode_mono_bmp_pixels all white 15x16',
        'input': {
            'pixels': pixels_all_white,
            'width': 15,
            'height': 16
        },
        'output': {
            'pixel_data': list(pixel_data)
        }
    })

    # Checkerboard pattern
    pixels_checker = [[(x + y) % 2 for x in range(15)] for y in range(16)]
    pixel_data = encode_mono_bmp_pixels(pixels_checker, 15, 16)
    tests.append({
        'name': 'encode_mono_bmp_pixels checkerboard 15x16',
        'input': {
            'pixels': pixels_checker,
            'width': 15,
            'height': 16
        },
        'output': {
            'pixel_data': list(pixel_data)
        }
    })

    # Single column
    pixels_column = [[1 if x == 0 else 0 for x in range(15)] for y in range(16)]
    pixel_data = encode_mono_bmp_pixels(pixels_column, 15, 16)
    tests.append({
        'name': 'encode_mono_bmp_pixels single column 15x16',
        'input': {
            'pixels': pixels_column,
            'width': 15,
            'height': 16
        },
        'output': {
            'pixel_data': list(pixel_data)
        }
    })

    return {'font_decoding': tests}


def generate_misalignment_test_data():
    """Generate test cases for offset table misalignment detection.

    Creates test data simulating scenarios where metadata table indices are
    misaligned with ROCK26 resource table indices. This can occur due to
    firmware structure variations.

    Test Cases:
    - +1 index shift: metadata[1] corresponds to ROCK26[0]
    - No misalignment: indices align perfectly

    Returns:
        Dictionary containing test cases under 'misalignment_detection' key.
    """
    print("Generating misalignment detection test data...")

    tests = []
    rock26_offsets = [0x1000, 0x1100, 0x1200, 0x1300, 0x1400]
    metadata_entries = [
        {'index': 0, 'offset': 0x0000, 'width': 10, 'height': 10, 'name': 'INVALID.BMP'},  # Invalid entry 0
        {'index': 1, 'offset': 0x1000, 'width': 100, 'height': 100, 'name': 'IMG001.BMP'},  # Matches ROCK26[0]
        {'index': 2, 'offset': 0x1100, 'width': 100, 'height': 100, 'name': 'IMG002.BMP'},  # Matches ROCK26[1]
        {'index': 3, 'offset': 0x1200, 'width': 100, 'height': 100, 'name': 'IMG003.BMP'},
        {'index': 4, 'offset': 0x1300, 'width': 100, 'height': 100, 'name': 'IMG004.BMP'},
        {'index': 5, 'offset': 0x1400, 'width': 100, 'height': 100, 'name': 'IMG005.BMP'},
    ]

    # Simulate detection logic
    offset_shift_votes = {}
    for rock26_idx in range(len(rock26_offsets)):
        rock26_offset_val = rock26_offsets[rock26_idx]
        for shift in range(-3, 4):
            metadata_idx = rock26_idx + shift
            if 0 <= metadata_idx < len(metadata_entries):
                metadata_offset_val = metadata_entries[metadata_idx]['offset']
                if metadata_offset_val == rock26_offset_val:
                    offset_shift_votes[shift] = offset_shift_votes.get(shift, 0) + 1

    best_shift = max(offset_shift_votes.items(), key=lambda x: x[1])[0] if offset_shift_votes else 0
    confidence = offset_shift_votes.get(best_shift, 0)

    tests.append({
        'name': 'misalignment_detection +1 shift',
        'input': {
            'rock26_offsets': rock26_offsets,
            'metadata_entries': metadata_entries
        },
        'output': {
            'offset_shift_votes': offset_shift_votes,
            'best_shift': best_shift,
            'confidence': confidence
        }
    })

    # Test case 2: No misalignment
    metadata_entries_aligned = [
        {'index': 0, 'offset': 0x1000, 'width': 100, 'height': 100, 'name': 'IMG001.BMP'},
        {'index': 1, 'offset': 0x1100, 'width': 100, 'height': 100, 'name': 'IMG002.BMP'},
        {'index': 2, 'offset': 0x1200, 'width': 100, 'height': 100, 'name': 'IMG003.BMP'},
    ]

    offset_shift_votes = {}
    for rock26_idx in range(len(rock26_offsets)):
        rock26_offset_val = rock26_offsets[rock26_idx]
        for shift in range(-3, 4):
            metadata_idx = rock26_idx + shift
            if 0 <= metadata_idx < len(metadata_entries_aligned):
                metadata_offset_val = metadata_entries_aligned[metadata_idx]['offset']
                if metadata_offset_val == rock26_offset_val:
                    offset_shift_votes[shift] = offset_shift_votes.get(shift, 0) + 1

    best_shift = max(offset_shift_votes.items(), key=lambda x: x[1])[0] if offset_shift_votes else 0
    confidence = offset_shift_votes.get(best_shift, 0)

    tests.append({
        'name': 'misalignment_detection no shift (aligned)',
        'input': {
            'rock26_offsets': rock26_offsets[:3],
            'metadata_entries': metadata_entries_aligned
        },
        'output': {
            'offset_shift_votes': offset_shift_votes,
            'best_shift': best_shift,
            'confidence': confidence
        }
    })

    return {'misalignment_detection': tests}


def main():
    """Main entry point for test data generation.

    Generates comprehensive test data for all functions and writes to a JSON file
    that can be consumed by TypeScript tests for verification.
    """
    print("=" * 80)
    print("Python Test Data Generator")
    print("=" * 80)

    output_dir = Path(__file__).parent.parent / 'src' / 'lib' / 'rse' / '__tests__' / 'data'
    output_dir.mkdir(parents=True, exist_ok=True)

    all_test_data = {}
    all_test_data.update(generate_bitmap_test_data())
    all_test_data.update(generate_font_test_data())
    all_test_data.update(generate_misalignment_test_data())

    output_file = output_dir / 'python_test_data.json'
    with open(output_file, 'w') as f:
        json.dump(all_test_data, f, indent=2)

    print(f"\nTest data written to: {output_file}")

    total_tests = sum(len(v) if isinstance(v, list) else 1 for v in all_test_data.values())
    print(f"Total test cases: {total_tests}")

    for category, tests in all_test_data.items():
        count = len(tests) if isinstance(tests, list) else 1
        print(f"  {category}: {count} tests")

    print("\n" + "=" * 80)
    print("Test data generation complete!")
    print("=" * 80)


if __name__ == '__main__':
    main()
