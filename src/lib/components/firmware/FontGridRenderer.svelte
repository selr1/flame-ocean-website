<script lang="ts">
	import { onMount } from 'svelte';

	interface FontData {
		unicode: number;
		fontType: 'SMALL' | 'LARGE';
		pixels: boolean[][];
	}

	interface Props {
		fonts: FontData[];
		zoom?: number;
	}

	let { fonts, zoom = 10 }: Props = $props();

	let canvasElement: HTMLCanvasElement;
	let ctx: CanvasRenderingContext2D;

	const FONT_WIDTH = 15;
	const FONT_HEIGHT = 16;
	const COLUMNS = 16;

	onMount(() => {
		const canvas = canvasElement;
		ctx = canvas.getContext('2d')!;
		render();
	});

	$effect(() => {
		if (ctx) {
			render();
		}
	});

	function render() {
		if (!fonts.length || !ctx) return;

		// Calculate canvas size
		const rows = Math.ceil(fonts.length / COLUMNS);
		const cellWidth = FONT_WIDTH * zoom + 20; // Extra space for label
		const cellHeight = FONT_HEIGHT * zoom + 20;

		canvasElement.width = cellWidth * COLUMNS;
		canvasElement.height = cellHeight * rows;

		// Clear canvas
		ctx.fillStyle = '#c0c0c0'; // Windows 98 gray
		ctx.fillRect(0, 0, canvasElement.width, canvasElement.height);

		// Draw each font
		for (let i = 0; i < fonts.length; i++) {
			const font = fonts[i];
			const col = i % COLUMNS;
			const row = Math.floor(i / COLUMNS);

			const x = col * cellWidth;
			const y = row * cellHeight;

			// Draw border
			ctx.strokeStyle = '#808080';
			ctx.lineWidth = 1;
			ctx.strokeRect(x + 2, y + 2, FONT_WIDTH * zoom + 16, FONT_HEIGHT * zoom + 16);

			// Draw font pixels
			for (let py = 0; py < font.pixels.length; py++) {
				for (let px = 0; px < font.pixels[py].length; px++) {
					if (font.pixels[py][px]) {
						ctx.fillStyle = '#000000';
						ctx.fillRect(
							x + 10 + px * zoom,
							y + 10 + py * zoom,
							zoom,
							zoom
						);
					}
				}
			}

			// Draw Unicode label
			ctx.fillStyle = '#000000';
			ctx.font = `${Math.max(8, zoom)}px monospace`;
			const hex = 'U+' + font.unicode.toString(16).padStart(4, '0').toUpperCase();
			ctx.fillText(hex, x + 10, y + FONT_HEIGHT * zoom + 14);
		}
	}
</script>

<canvas bind:this={canvasElement} class="font-grid-canvas"></canvas>

<style>
	.font-grid-canvas {
		display: block;
		background-color: #c0c0c0;
		border: 2px solid;
		border-color: #dfdfdf #808080 #808080 #dfdfdf;
	}
</style>
