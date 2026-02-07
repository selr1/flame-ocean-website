/**
 * Test to verify ResourceExtractor produces images with same dimensions as Python ground truth
 *
 * Ground truth location: /home/losses/Downloads/ECHO MINI V3.1.0/extracted_bitmaps_smart/batch_20260207_112124/
 * Ground truth filenames contain dimensions like: AAKEY32_(182,284).BMP (width=182, height=284)
 */

import { describe, it, expect } from 'vitest';
import { ResourceExtractor } from './extractors/resource-extractor.js';
import { readdirSync, existsSync } from 'fs';
import { join } from 'path';

interface GroundTruthEntry {
	name: string;
	width: number;
	height: number;
	version: string;
}

interface FirmwareInfo {
	version: string;
	path: string;
}

/**
 * Parse dimensions from ground truth filename
 * Format: NAME_(width,height).BMP
 * Example: AAKEY32_(182,284).BMP -> { width: 182, height: 284, name: "AAKEY32" }
 */
function parseGroundTruthFilename(filename: string): GroundTruthEntry | null {
	// Match pattern: NAME_(width,height).BMP
	const match = filename.match(/^(.+)_\((\d+),(\d+)\)\.BMP$/i);
	if (!match) {
		return null;
	}

	const [, name, widthStr, heightStr] = match;
	const width = parseInt(widthStr, 10);
	const height = parseInt(heightStr, 10);

	if (isNaN(width) || isNaN(height)) {
		return null;
	}

	return { name, width, height, version: '' };
}

/**
 * Load all ground truth entries from a version folder
 */
function loadGroundTruth(versionFolder: string): Map<string, GroundTruthEntry> {
	const entries = new Map<string, GroundTruthEntry>();

	if (!existsSync(versionFolder)) {
		return entries;
	}

	const files = readdirSync(versionFolder);
	for (const file of files) {
		const parsed = parseGroundTruthFilename(file);
		if (parsed) {
			entries.set(parsed.name.toUpperCase(), parsed);
		}
	}

	return entries;
}

/**
 * Find all available firmware files and their version names
 */
function findFirmwareFiles(): FirmwareInfo[] {
	const basePath = '/home/losses/Downloads/ECHO MINI V3.1.0/firmwares';
	const versions = ['ECHO MINI V1.2.5', 'ECHO MINI V1.2.7', 'ECHO MINI V1.8.0',
		'ECHO MINI V2.4.0', 'ECHO MINI V2.5.0', 'ECHO MINI V2.6.0',
		'ECHO MINI V2.8.0', 'ECHO MINI V3.0.0', 'ECHO MINI V3.1.0',
		'EHCO MINI V1.3.0'];

	const results: FirmwareInfo[] = [];

	for (const version of versions) {
		// Find IMG file (may have different numbers)
		const versionDir = join(basePath, version);
		if (existsSync(versionDir)) {
			const files = readdirSync(versionDir).filter(f => f.endsWith('.IMG'));
			for (const file of files) {
				results.push({
					version,
					path: join(versionDir, file)
				});
			}
		}
	}

	return results;
}

describe('ResourceExtractor - Ground Truth Dimensions Comparison', () => {
	const GROUND_TRUTH_BASE = '/home/losses/Downloads/ECHO MINI V3.1.0/extracted_bitmaps_smart/batch_20260207_112124';

	it('should match all dimensions for ECHO MINI V3.1.0', () => {
		const version = 'ECHO MINI V3.1.0';
		const firmwarePath = '/home/losses/Downloads/ECHO MINI V3.1.0/firmwares/ECHO MINI V3.1.0/HIFIEC10.IMG';
		const groundTruthPath = join(GROUND_TRUTH_BASE, version);

		// Load ground truth
		const groundTruth = loadGroundTruth(groundTruthPath);

		expect(groundTruth.size, `Ground truth folder should contain entries`).toBeGreaterThan(0);

		// Extract using TypeScript implementation
		const extractor = new ResourceExtractor(firmwarePath);
		const bitmapList = extractor.listDirectory();

		// Track mismatches
		const mismatches: { name: string; ts: { width: number; height: number }; gt: { width: number; height: number } }[] = [];
		const missingInGT: string[] = [];
		const missingInTS: string[] = [];

		// Compare each TypeScript entry with ground truth
		for (const tsEntry of bitmapList) {
			const key = tsEntry.name.toUpperCase();
			const gtEntry = groundTruth.get(key);

			if (!gtEntry) {
				// Check if there's a similar entry with dimensions stripped
				// Some ground truth entries might have names like "POWERON1_(0,0)" in the metadata
				// Let's try to find by checking if any GT entry contains this name
				let found = false;
				for (const [gtKey, gtVal] of groundTruth) {
					if (gtKey === key || gtKey.replace(/_\(\d+,\d+\)$/, '') === key) {
						// Found matching GT entry
						if (tsEntry.width !== gtVal.width || tsEntry.height !== gtVal.height) {
							mismatches.push({
								name: tsEntry.name,
								ts: { width: tsEntry.width, height: tsEntry.height },
								gt: { width: gtVal.width, height: gtVal.height }
							});
						}
						groundTruth.delete(gtKey);
						found = true;
						break;
					}
				}
				if (!found) {
					missingInGT.push(tsEntry.name);
				}
				continue;
			}

			// Check dimensions match
			if (tsEntry.width !== gtEntry.width || tsEntry.height !== gtEntry.height) {
				mismatches.push({
					name: tsEntry.name,
					ts: { width: tsEntry.width, height: tsEntry.height },
					gt: { width: gtEntry.width, height: gtEntry.height }
				});
			}

			// Remove from map to track TS entries we've checked
			groundTruth.delete(key);
		}

		// Any remaining entries in groundTruth are missing from TS
		for (const [name] of groundTruth) {
			missingInTS.push(name);
		}

		// Report results
		console.log(`\n=== Version: ${version} ===`);
		console.log(`Total TypeScript entries: ${bitmapList.length}`);
		console.log(`Total Ground Truth entries: ${groundTruth.size + bitmapList.length - missingInGT.length}`);
		console.log(`Matching dimensions: ${bitmapList.length - mismatches.length}`);
		console.log(`Dimension mismatches: ${mismatches.length}`);
		console.log(`Missing in Ground Truth: ${missingInGT.length}`);
		console.log(`Missing in TypeScript: ${missingInTS.length}`);

		if (mismatches.length > 0) {
			console.log(`\n=== Dimension Mismatches (first 20) ===`);
			for (const m of mismatches.slice(0, 20)) {
				console.log(`  ${m.name}: TS=${m.ts.width}x${m.ts.height}, GT=${m.gt.width}x${m.gt.height}`);
			}
		}

		if (missingInGT.length > 0) {
			console.log(`\n=== Missing in Ground Truth (first 10) ===`);
			for (const name of missingInGT.slice(0, 10)) {
				console.log(`  ${name}`);
			}
		}

		if (missingInTS.length > 0) {
			console.log(`\n=== Missing in TypeScript (first 10) ===`);
			for (const name of missingInTS.slice(0, 10)) {
				console.log(`  ${name}`);
			}
		}

		// Assert that dimensions match
		expect(mismatches.length, `Should have no dimension mismatches`).toBe(0);
	});

	/**
	 * Quick test for all versions to identify which versions have issues
	 */
	it('should check all versions for dimension mismatches', () => {
		const firmwares = findFirmwareFiles();

		console.log(`\n=== All Versions Summary ===`);
		console.log(`Found ${firmwares.length} firmware files`);

		const results: Array<{
			version: string;
			total: number;
			mismatches: number;
			sampleMismatches: string[];
		}> = [];

		for (const { version, path } of firmwares) {
			const groundTruthPath = join(GROUND_TRUTH_BASE, version);
			if (!existsSync(groundTruthPath)) {
				console.log(`  ${version}: No ground truth folder found`);
				continue;
			}

			const groundTruth = loadGroundTruth(groundTruthPath);
			if (groundTruth.size === 0) {
				console.log(`  ${version}: No ground truth entries found`);
				continue;
			}

			const extractor = new ResourceExtractor(path);
			const bitmapList = extractor.listDirectory();

			let mismatches = 0;
			const sampleMismatches: string[] = [];

			for (const tsEntry of bitmapList) {
				const key = tsEntry.name.toUpperCase();
				const gtEntry = groundTruth.get(key);

				if (gtEntry) {
					if (tsEntry.width !== gtEntry.width || tsEntry.height !== gtEntry.height) {
						mismatches++;
						if (sampleMismatches.length < 5) {
							sampleMismatches.push(
								`${tsEntry.name}: TS=${tsEntry.width}x${tsEntry.height}, GT=${gtEntry.width}x${gtEntry.height}`
							);
						}
					}
					groundTruth.delete(key);
				}
			}

			results.push({
				version,
				total: bitmapList.length,
				mismatches,
				sampleMismatches
			});

			console.log(`  ${version}: ${bitmapList.length} entries, ${mismatches} mismatches`);
			if (sampleMismatches.length > 0) {
				for (const s of sampleMismatches) {
					console.log(`    - ${s}`);
				}
			}
		}

		// Count how many versions have perfect matches
		const perfectMatches = results.filter(r => r.mismatches === 0).length;
		console.log(`\n=== Summary ===`);
		console.log(`Versions tested: ${results.length}`);
		console.log(`Perfect matches: ${perfectMatches}`);
		console.log(`Versions with mismatches: ${results.length - perfectMatches}`);

		// All versions should have no mismatches
		results.forEach(r => {
			expect(r.mismatches, `${r.version} should have no dimension mismatches`).toBe(0);
		});
	});

	/**
	 * Test specific sample entries that are known to be problematic
	 */
	it('should verify first 10 entries match ground truth exactly', () => {
		const version = 'ECHO MINI V3.1.0';
		const firmwarePath = '/home/losses/Downloads/ECHO MINI V3.1.0/firmwares/ECHO MINI V3.1.0/HIFIEC10.IMG';
		const groundTruthPath = join(GROUND_TRUTH_BASE, version);

		const groundTruth = loadGroundTruth(groundTruthPath);
		const extractor = new ResourceExtractor(firmwarePath);
		const bitmapList = extractor.listDirectory();

		// Get first 10 entries
		const first10 = bitmapList.slice(0, 10);

		console.log(`\n=== First 10 Entries Detail ===`);
		for (const entry of first10) {
			const gt = groundTruth.get(entry.name.toUpperCase());
			const gtStr = gt ? `${gt.width}x${gt.height}` : 'NOT_FOUND';
			console.log(`  ${entry.name.padEnd(30)} TS=${entry.width}x${entry.height} GT=${gtStr}`);

			if (gt) {
				expect(entry.width, `Width should match for ${entry.name}`).toBe(gt.width);
				expect(entry.height, `Height should match for ${entry.name}`).toBe(gt.height);
			}
		}
	});
});
