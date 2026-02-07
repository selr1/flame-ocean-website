<script lang="ts">
	import type { Snippet } from 'svelte';
	import { clsx } from 'clsx';
	import TitleBar from './TitleBar.svelte';
	import WindowBody from './WindowBody.svelte';
	import StatusBar from './StatusBar.svelte';
	import ProgressBar from './ProgressBar.svelte';

	interface StatusField {
		text: string;
		class?: string;
	}

	interface Props {
		title?: string;
		message?: string;
		progress?: number;
		showProgress?: boolean;
		width?: string;
		children?: Snippet;
		statusFields?: StatusField[];
	}

	let {
		title = 'Processing',
		message,
		progress = 0,
		showProgress = true,
		width = '400px',
		children,
		statusFields
	}: Props = $props();
</script>

<div class="loading-overlay">
	<div class="loading-window" style="width: {width};">
		<TitleBar>
			{title}
		</TitleBar>

		<WindowBody>
			{#if showProgress}
				<ProgressBar value={progress} />
			{/if}

			{#if message}
				<p class="loading-message">{message}</p>
			{/if}

			{#if children}
				{@render children()}
			{/if}
		</WindowBody>

		{#if statusFields && statusFields.length > 0}
			<StatusBar {statusFields} />
		{/if}
	</div>
</div>

<style>
	.loading-overlay {
		position: fixed;
		top: 0;
		left: 0;
		right: 0;
		bottom: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		background-color: rgba(0, 0, 0, 0.3);
		z-index: 9999;
	}

	.loading-window {
		box-shadow: 4px 4px 0 rgba(0, 0, 0, 0.5);
	}

	.loading-message {
		margin: 12px 0 0 0;
		font-size: 12px;
		color: #000000;
		text-align: center;
	}
</style>
