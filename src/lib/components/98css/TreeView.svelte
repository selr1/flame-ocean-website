<script lang="ts">
	import type { Snippet } from 'svelte';
	import type { ClassValue } from 'svelte/elements';
	import { clsx } from 'clsx';

	interface TreeNode {
		id: string;
		label: string;
		children?: TreeNode[];
		expanded?: boolean;
		disabled?: boolean;
	}

	interface Props {
		class?: ClassValue;
		nodes: TreeNode[];
		expanded?: Set<string>;
		onToggle?: (nodeId: string) => void;
		onSelect?: (nodeId: string) => void;
		children?: Snippet;
	}

	let { class: className, nodes, expanded = $bindable(new Set<string>()), onToggle, onSelect, children }: Props =
		$props();

	const treeViewClass = $derived(clsx('tree-view', className));

	function toggleNode(nodeId: string): void {
		const newExpanded = new Set(expanded);
		if (expanded.has(nodeId)) {
			newExpanded.delete(nodeId);
		} else {
			newExpanded.add(nodeId);
		}
		expanded = newExpanded;
		onToggle?.(nodeId);
	}

	function isExpanded(nodeId: string): boolean {
		return expanded.has(nodeId);
	}

	function handleLeafKeydown(nodeId: string, e: KeyboardEvent) {
		if (e.key === 'Enter' || e.key === ' ') {
			e.preventDefault();
			onSelect?.(nodeId);
		}
	}
</script>

<ul class={treeViewClass}>
	{#each nodes as node (node.id)}
		<li>
			{#if node.children && node.children.length > 0}
				<details open={isExpanded(node.id)} ontoggle={() => toggleNode(node.id)}>
					<summary>{node.label}</summary>
					<ul>
						{#each node.children as child (child.id)}
							<li>
								{#if child.children && child.children.length > 0}
									<details open={isExpanded(child.id)} ontoggle={() => toggleNode(child.id)}>
										<summary>{child.label}</summary>
										<ul>
											{#each child.children as grandchild (grandchild.id)}
												<li>
													{#if grandchild.children && grandchild.children.length > 0}
														{grandchild.label}
													{:else}
														<span
															class="leaf-node"
															onclick={() => onSelect?.(grandchild.id)}
															onkeydown={(e) => handleLeafKeydown(grandchild.id, e)}
															role="button"
															tabindex="0"
														>
															{grandchild.label}
														</span>
													{/if}
												</li>
											{/each}
										</ul>
									</details>
								{:else}
									<span
										class="leaf-node"
										onclick={() => onSelect?.(child.id)}
										onkeydown={(e) => handleLeafKeydown(child.id, e)}
										role="button"
										tabindex="0"
									>
										{child.label}
									</span>
								{/if}
							</li>
						{/each}
					</ul>
				</details>
			{:else}
				<span
					class="leaf-node"
					onclick={() => onSelect?.(node.id)}
					onkeydown={(e) => handleLeafKeydown(node.id, e)}
					role="button"
					tabindex="0"
				>
					{node.label}
				</span>
			{/if}
		</li>
	{/each}
	{#if children}
		{@render children()}
	{/if}
</ul>

<style>
	.leaf-node {
		cursor: pointer;
		padding: 2px 4px;
		display: inline-block;
	}

	.leaf-node:hover {
		background-color: #000080;
		color: #ffffff;
	}

	.leaf-node:focus {
		outline: 1px dotted #000000;
	}
</style>
