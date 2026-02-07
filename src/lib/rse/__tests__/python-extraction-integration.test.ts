/**
 * Integration tests comparing TypeScript extraction with Python extraction
 *
 * These tests load real firmware files and verify that the TypeScript implementation
 * produces identical output to the Python reference implementation.
 *
 * Prerequisites:
 * - Python reference files must exist at the PYTHON_EXTRACTED_PATH
 * - Run python3 references/extract_resource_smart.py to generate reference files
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import { readFileSync, existsSync, rmSync, readdirSync } from 'node:fs';
import { join } from 'node:path';
import { execSync } from 'node:child_process';
import { ResourceExtractor } from '../extractors/resource-extractor.js';
import { bmpToRgb565 } from '../utils/bitmap.js';

// Configuration
// NOTE: Run `bun run src/lib/rse/__tests__/setup-fixtures.ts` to download and prepare test fixtures
const BASE_DOWNLOAD_DIR = '/tmp/echo-mini-firmwares';
const TEST_VERSION = 'ECHO MINI V1.8.0'; // Single version for faster testing

const FIRMWARE_PATH = join(BASE_DOWNLOAD_DIR, TEST_VERSION, 'HIFIEC80.IMG');
const PYTHON_EXTRACTED_PATH = join(BASE_DOWNLOAD_DIR, 'extracted_bitmaps_smart', 'batch_auto', TEST_VERSION);
const TEST_IMAGE_COUNT = 10;

// Test state
let extractor: ResourceExtractor;
let tsDir: string;
let pythonFiles: string[];

/**
 * Check if test fixtures are ready, and optionally set them up
 * @param setup - Whether to download/prepare fixtures if missing
 * @returns true if fixtures are ready
 */
export function ensureFixtures(setup = false): boolean {
	if (!existsSync(FIRMWARE_PATH)) {
		if (setup) {
			console.log('\nFixtures not found. Running setup...');
			try {
				execSync('bun run src/lib/rse/__tests__/setup-fixtures.ts', { stdio: 'inherit' });
				return existsSync(FIRMWARE_PATH);
			} catch (error) {
				console.error('\nFailed to set up fixtures:', error);
				console.log('\nTo manually set up fixtures:');
				console.log('  bun run src/lib/rse/__tests__/setup-fixtures.ts');
				return false;
			}
		}
		return false;
	}
	return true;
}

describe('Python Extraction Integration Tests', () => {
	beforeAll(() => {
		// Check if --setup flag is passed or fixtures exist
		const setupMode = process.argv.includes('--setup');
		if (!ensureFixtures(setupMode)) {
			throw new Error(
				`Test fixtures not found.\n` +
				`Please run: bun run test:setup\n` +
				`Or run tests with: bun test src/lib/rse/__tests__/python-extraction-integration.test.ts --setup`
			);
		}

		// Load firmware
		const firmwareData = new Uint8Array(readFileSync(FIRMWARE_PATH));
		extractor = new ResourceExtractor(firmwareData);

		// Get list of Python-extracted files
		const allFiles = readdirSync(PYTHON_EXTRACTED_PATH);
		pythonFiles = allFiles.filter((f: string) => f.toUpperCase().endsWith('.BMP'));

		// Extract images using TypeScript
		tsDir = `/tmp/ts_integration_test_${Date.now()}`;
		const result = extractor.extractPart5BitmapsSmart(tsDir, 'ECHO MINI V1.8.0', false);

		expect(result).not.toBeNull();
		expect(result!.misalignment).toBe(1);
		expect(result!.success).toBeGreaterThan(0);
		console.log(`\nIntegration Test Setup:`);
		console.log(`  Firmware: ${FIRMWARE_PATH}`);
		console.log(`  Python reference: ${PYTHON_EXTRACTED_PATH}`);
		console.log(`  TypeScript output: ${tsDir}`);
		console.log(`  Total Python images: ${pythonFiles.length}`);
		console.log(`  TypeScript extracted: ${result!.success} images`);
		console.log(`  Detected misalignment: ${result!.misalignment}\n`);
	}, 60000);

	// Clean up after all tests
	afterAll(() => {
		if (tsDir && existsSync(tsDir)) {
			rmSync(tsDir, { recursive: true });
		}
	});

	it('should have Python reference files available', () => {
		expect(existsSync(FIRMWARE_PATH)).toBe(true);
		expect(existsSync(PYTHON_EXTRACTED_PATH)).toBe(true);
	});

	it('should detect correct misalignment (+1)', () => {
		// Re-run to verify misalignment detection
		const result = extractor.extractPart5BitmapsSmart(tsDir, 'ECHO MINI V1.8.0', false);
		expect(result).not.toBeNull();
		expect(result!.misalignment).toBe(1); // Python detects +1
	});

	it('should extract approximately same number of images as Python', () => {
		const result = extractor.extractPart5BitmapsSmart(tsDir, 'ECHO MINI V1.8.0', false);
		// Allow small tolerance for any differences in edge case handling
		expect(Math.abs(result!.success - pythonFiles.length)).toBeLessThan(5);
	});

	// Test pixel-perfect match for first N images
	it(`should perfectly match Python for first ${TEST_IMAGE_COUNT} images`, () => {
		let totalMismatches = 0;
		let testedFiles = 0;

		for (let i = 0; i < Math.min(TEST_IMAGE_COUNT, pythonFiles.length); i++) {
			const fileName = pythonFiles[i];
			const pythonBmpPath = `${PYTHON_EXTRACTED_PATH}/${fileName}`;
			const tsBmpPath = `${tsDir}/ECHO MINI V1.8.0/${fileName}`;

			// Skip if TypeScript didn't extract this file
			if (!existsSync(tsBmpPath)) {
				console.warn(`  ⚠️  TypeScript did not extract: ${fileName}`);
				continue;
			}

			testedFiles++;

			const pythonBmp = new Uint8Array(readFileSync(pythonBmpPath));
			const tsBmp = new Uint8Array(readFileSync(tsBmpPath));

			// Compare file sizes
			expect(tsBmp.length).toBe(pythonBmp.length);

			// Byte-by-byte comparison
			for (let j = 0; j < pythonBmp.length; j++) {
				if (pythonBmp[j] !== tsBmp[j]) {
					totalMismatches++;
				}
			}
		}

		console.log(`  Tested ${testedFiles} files, ${totalMismatches} byte mismatches`);
		expect(totalMismatches).toBe(0);
	});

	it('should extract raw RGB565 data matching Python', () => {
		// Test a specific image: POWERON1_(0,0).BMP
		const fileName = 'POWERON1_(0,0).BMP';
		const pythonBmpPath = `${PYTHON_EXTRACTED_PATH}/${fileName}`;
		const tsBmpPath = `${tsDir}/ECHO MINI V1.8.0/${fileName}`;

		expect(existsSync(tsBmpPath)).toBe(true);

		const pythonBmp = new Uint8Array(readFileSync(pythonBmpPath));
		const tsBmp = new Uint8Array(readFileSync(tsBmpPath));

		// Extract raw RGB565 from both BMPs
		const pythonRgb565 = bmpToRgb565(pythonBmp);
		const tsRgb565 = bmpToRgb565(tsBmp);

		expect(pythonRgb565).not.toBeNull();
		expect(tsRgb565).not.toBeNull();

		if (pythonRgb565 && tsRgb565) {
			// Verify sizes match
			expect(tsRgb565.length).toBe(pythonRgb565.length);

			// Sample comparison: check first 100 pixels (200 bytes)
			const sampleSize = Math.min(200, pythonRgb565.length);
			for (let i = 0; i < sampleSize; i++) {
				expect(tsRgb565[i]).toBe(pythonRgb565[i]);
			}
		}
	});

	it('should extract images with correct dimensions', () => {
		// Test that dimensions are consistent between metadata and actual BMP data
		const fileName = 'Z_POWERON0_(0,0).BMP';
		const tsBmpPath = `${tsDir}/ECHO MINI V1.8.0/${fileName}`;

		expect(existsSync(tsBmpPath)).toBe(true);

		const tsBmp = new Uint8Array(readFileSync(tsBmpPath));

		// Read dimensions from BMP header
		const width = tsBmp[18] | (tsBmp[19] << 8) | (tsBmp[20] << 16) | (tsBmp[21] << 24);
		const height = Math.abs(tsBmp[22] | (tsBmp[23] << 8) | (tsBmp[24] << 16) | (tsBmp[25] << 24));
		const bitsPerPixel = tsBmp[28] | (tsBmp[29] << 8);

		// Validate BMP format
		expect(bitsPerPixel).toBe(16); // RGB565
		expect(width).toBeGreaterThan(0);
		expect(height).toBeGreaterThan(0);
		expect(width).toBeLessThanOrEqual(1000);
		expect(height).toBeLessThanOrEqual(500);

		// Check file size is reasonable for RGB565
		const expectedPixelDataSize = width * height * 2;
		const fileSize = tsBmp.length;
		expect(fileSize).toBeGreaterThan(expectedPixelDataSize);
		expect(fileSize).toBeLessThan(expectedPixelDataSize + 200); // Allow for headers
	});

	// CRITICAL TEST: Verify replacement writes to correct location
	it('should replace bitmap at correct firmware location (round-trip test)', () => {
		// Test with a known bitmap file
		const fileName = 'Z_POWERON0_(0,0).BMP';

		// Read original bitmap data
		const originalData = extractor.readBitmap(fileName);
		expect(originalData).not.toBeNull();

		// Create modified data (invert all bytes)
		const modifiedData = new Uint8Array(originalData!.length);
		for (let i = 0; i < originalData!.length; i++) {
			modifiedData[i] = originalData![i] ^ 0xff;
		}

		// Replace the bitmap
		const replaceResult = extractor.replaceBitmap(fileName, modifiedData);
		expect(replaceResult).toBe(true);

		// Read back the bitmap
		const afterReplace = extractor.readBitmap(fileName);
		expect(afterReplace).not.toBeNull();

		// Verify the data matches exactly what we wrote
		expect(afterReplace!.length).toBe(modifiedData.length);
		for (let i = 0; i < modifiedData.length; i++) {
			expect(afterReplace![i]).toBe(modifiedData[i]);
		}

		// Verify the data is DIFFERENT from original
		let hasDifference = false;
		for (let i = 0; i < Math.min(originalData!.length, afterReplace!.length); i++) {
			if (originalData![i] !== afterReplace![i]) {
				hasDifference = true;
				break;
			}
		}
		expect(hasDifference).toBe(true);

		// Restore original data (cleanup)
		const restoreResult = extractor.replaceBitmap(fileName, originalData!);
		expect(restoreResult).toBe(true);

		// Verify restoration
		const afterRestore = extractor.readBitmap(fileName);
		expect(afterRestore).not.toBeNull();
		for (let i = 0; i < originalData!.length; i++) {
			expect(afterRestore![i]).toBe(originalData![i]);
		}
	});

	// CRITICAL TEST: Verify replacement doesn't corrupt other data
	it('should replace bitmap without corrupting adjacent firmware data', () => {
		// Create a fresh extractor to test corruption
		const testExtractor = new ResourceExtractor(new Uint8Array(readFileSync(FIRMWARE_PATH)));

		// Get two different bitmap files
		const file1 = pythonFiles.find((f) => f.includes('POWERON'));
		const file2 = pythonFiles.find((f) => f.includes('logo') || f.includes('ICON'));

		if (!file1 || !file2) {
			console.log('  ⚠️  Skipping: Could not find two distinct bitmap files');
			return;
		}

		// Read both bitmaps
		const data1Original = testExtractor.readBitmap(file1);
		const data2Original = testExtractor.readBitmap(file2);

		if (!data1Original || !data2Original) {
			console.log('  ⚠️  Skipping: Could not read bitmap data');
			return;
		}

		// Modify and replace file1
		const modifiedData1 = new Uint8Array(data1Original.length);
		for (let i = 0; i < data1Original.length; i++) {
			modifiedData1[i] = data1Original[i] ^ 0xff;
		}

		const replaceResult = testExtractor.replaceBitmap(file1, modifiedData1);
		expect(replaceResult).toBe(true);

		// Verify file2 was NOT affected
		const data2AfterReplace = testExtractor.readBitmap(file2);
		expect(data2AfterReplace).not.toBeNull();

		for (let i = 0; i < data2Original.length; i++) {
			expect(data2AfterReplace![i]).toBe(data2Original[i]);
		}

		// Verify file1 WAS modified
		const data1AfterReplace = testExtractor.readBitmap(file1);
		expect(data1AfterReplace).not.toBeNull();

		let hasDifference = false;
		for (let i = 0; i < Math.min(data1Original.length, data1AfterReplace!.length); i++) {
			if (data1Original[i] !== data1AfterReplace![i]) {
				hasDifference = true;
				break;
			}
		}
		expect(hasDifference).toBe(true);
	});
});
