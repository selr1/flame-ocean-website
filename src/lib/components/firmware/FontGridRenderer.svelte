<script lang="ts">
	import { Grid } from 'svelte-virtual';

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

	const FONT_WIDTH = 15;
	const FONT_HEIGHT = 16;

	// Calculate item dimensions (reactive)
	const itemWidth = $derived(FONT_WIDTH * zoom + 20);
	const itemHeight = $derived(FONT_HEIGHT * zoom + 30);
	const itemCount = $derived(fonts.length);

	// Helper function to get hex string
	function getHexString(unicode: number): string {
		return 'U+' + unicode.toString(16).padStart(4, '0').toUpperCase();
	}

	// Action to render font on canvas
	function renderFont(canvas: HTMLCanvasElement, font: FontData) {
		function draw() {
			const ctx = canvas.getContext('2d');
			if (!ctx) return;

			// Set canvas size
			canvas.width = FONT_WIDTH * zoom;
			canvas.height = FONT_HEIGHT * zoom;

			// Clear canvas
			ctx.clearRect(0, 0, canvas.width, canvas.height);

			// Draw font pixels
			for (let py = 0; py < font.pixels.length; py++) {
				for (let px = 0; px < font.pixels[py].length; px++) {
					if (font.pixels[py][px]) {
						ctx.fillStyle = '#000000';
						ctx.fillRect(px * zoom, py * zoom, zoom, zoom);
					}
				}
			}
		}

		draw();

		return {
			update: (newFont: FontData) => {
				if (newFont !== font) {
					draw();
				}
			}
		};
	}
</script>

<div class="font-grid-container">
	<Grid
		itemCount={itemCount}
		itemWidth={itemWidth}
		itemHeight={itemHeight}
		height={600}
	>
		<div slot="item" let:index let:style class="font-item" {style}>
			<div class="canvas-wrapper">
				<canvas
					use:renderFont={fonts[index]}
					class="font-canvas"
					width={FONT_WIDTH * zoom}
					height={FONT_HEIGHT * zoom}
				></canvas>
			</div>
			<div class="unicode-label">{getHexString(fonts[index].unicode)}</div>
		</div>
	</Grid>
</div>

<style>
	.font-grid-container {
		display: block;
		background-color: #c0c0c0;
		border: 2px solid;
		border-color: #dfdfdf #808080 #808080 #dfdfdf;
		padding: 4px;
	}

	.font-item {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		padding: 4px;
		box-sizing: border-box;
	}

	.canvas-wrapper {
		border: 2px solid;
		border-color: #808080 #dfdfdf #dfdfdf #808080;
		padding: 2px;
		background-color: #ffffff;
		display: inline-block;
	}

	.font-canvas {
		display: block;
		image-rendering: pixelated;
	}

	.unicode-label {
		font-family: monospace;
		font-size: 10px;
		color: #000000;
		margin-top: 4px;
		text-align: center;
	}
</style>
