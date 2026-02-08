<script lang="ts">
  import type { BitmapFileInfo } from '../../rse/types';
  import { extractFrames } from '../../rse/utils/video-extractor';

  interface Props {
    targetImages: BitmapFileInfo[];
    onApply: (mappings: { target: BitmapFileInfo; source: File }[]) => void;
    onCancel: () => void;
  }

  let { targetImages, onApply, onCancel }: Props = $props();

  // Group parsing state
  interface ImageGroup {
    prefix: string;
    displayName: string;
    images: BitmapFileInfo[];
  }

  let selectedGroup = $state<ImageGroup | null>(null);
  let selectedImage = $state<BitmapFileInfo | null>(null);

  // Source file state
  let sourceFiles = $state<File[]>([]);
  let fileInput: HTMLInputElement;
  let isExtracting = $state(false);
  let previewUrl = $state<string | null>(null);
  let currentSourceIndex = $state(0);

  // Compute groups from target images (derived, no reactivity issues)
  let groups = $derived(parseImageGroups(targetImages));

  // Initialize selected group when groups change
  $effect(() => {
    if (groups.length > 0 && !selectedGroup) {
      selectedGroup = groups[0];
      selectedImage = groups[0].images[0] || null;
    }
  });

  // Parse images into groups based on filename patterns
  function parseImageGroups(images: BitmapFileInfo[]): ImageGroup[] {
    const groupMap = new Map<string, BitmapFileInfo[]>();

    for (const img of images) {
      const groupKey = extractGroupKey(img.name);
      // Skip images that don't match any pattern
      if (!groupKey.prefix) continue;

      if (!groupMap.has(groupKey.prefix)) {
        groupMap.set(groupKey.prefix, []);
      }
      groupMap.get(groupKey.prefix)!.push(img);
    }

    // Convert to array and sort
    return Array.from(groupMap.entries())
      .map(([prefix, imgs]) => ({
        prefix,
        displayName: prefix,
        images: imgs.sort((a, b) => a.name.localeCompare(b.name, undefined, { numeric: true }))
      }))
      .sort((a, b) => a.displayName.localeCompare(b.displayName));
  }

  // Extract group prefix from filename (e.g., "Z_POWERON0_(0,0).BMP" -> "Z_POWERON")
  function extractGroupKey(filename: string): { prefix: string; number: string } {
    // Pattern 1: Z_POWERON0_(0,0).BMP -> prefix: Z_POWERON
    const match1 = filename.match(/^(.+?)(\d+)[(](\d+),(\d+)[)][.]/);
    if (match1) {
      return { prefix: match1[1], number: match1[2] };
    }

    // Pattern 2: Z_POWERON_0_0.BMP -> prefix: Z_POWERON_
    const match2 = filename.match(/^(.+?)[_-](\d+)[_-](\d+)[_.]/);
    if (match2) {
      return { prefix: match2[1], number: match2[2] };
    }

    // Pattern 3: FRAME_0001.BMP -> prefix: FRAME_
    const match3 = filename.match(/^(.+?)[_-](\d+)[_.]/);
    if (match3) {
      const prefix = match3[1];
      // Add separator if not already present
      const finalPrefix = (prefix.endsWith('_') || prefix.endsWith('-')) ? prefix : prefix + '_';
      return { prefix: finalPrefix, number: match3[2] };
    }

    // No pattern found - return empty prefix to filter out this image
    return { prefix: '', number: '' };
  }

  // Select group and first image
  function selectGroup(group: ImageGroup) {
    selectedGroup = group;
    selectedImage = group.images[0] || null;
    currentSourceIndex = 0;
    cleanupPreview();
  }

  // Select image within group
  function selectImage(img: BitmapFileInfo, index: number) {
    selectedImage = img;
    currentSourceIndex = index;
    updatePreview();
  }

  async function processFiles(files: File[]) {
    if (files.length === 0) return;

    const videoFile = files.find(f => f.type.startsWith('video/'));

    if (videoFile) {
      isExtracting = true;
      try {
        const frames = await extractFrames(videoFile, selectedGroup?.images.length || 30);
        sourceFiles = frames;
      } catch (e) {
        console.error("Failed to extract frames", e);
        alert("Failed to extract frames from video: " + (e instanceof Error ? e.message : String(e)));
      } finally {
        isExtracting = false;
      }
    } else {
      sourceFiles = files;
    }
    updatePreview();
  }

  function handleFileSelect(e: Event) {
    const input = e.target as HTMLInputElement;
    if (input.files) {
      processFiles(Array.from(input.files));
    }
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer?.files) {
      processFiles(Array.from(e.dataTransfer.files));
    }
  }

  function handleDragOver(e: DragEvent) {
    e.preventDefault();
    e.stopPropagation();
  }

  function updatePreview() {
    cleanupPreview();
    if (sourceFiles[currentSourceIndex]) {
      const file = sourceFiles[currentSourceIndex];
      previewUrl = URL.createObjectURL(file);
    }
  }

  function cleanupPreview() {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      previewUrl = null;
    }
  }

  function nextImage() {
    if (!selectedGroup) return;
    const idx = selectedGroup.images.indexOf(selectedImage!);
    if (idx < selectedGroup.images.length - 1) {
      selectImage(selectedGroup.images[idx + 1], idx + 1);
    }
  }

  function prevImage() {
    if (!selectedGroup) return;
    const idx = selectedGroup.images.indexOf(selectedImage!);
    if (idx > 0) {
      selectImage(selectedGroup.images[idx - 1], idx - 1);
    }
  }

  function apply() {
    if (!selectedGroup || sourceFiles.length === 0) return;

    const mappings: { target: BitmapFileInfo; source: File }[] = [];
    for (let i = 0; i < selectedGroup.images.length && i < sourceFiles.length; i++) {
      mappings.push({
        target: selectedGroup.images[i],
        source: sourceFiles[i]
      });
    }

    if (mappings.length > 0) {
      onApply(mappings);
      cleanupPreview();
    }
  }

  // Cleanup on unmount
  $effect(() => {
    return () => cleanupPreview();
  });
</script>

<div class="sequence-replacer">
  <div class="header">
    <h3>Replace Image Sequence</h3>
    <p>Select a group, then load replacement files (or drop a video)</p>
  </div>

  <div class="content">
    <!-- Column 1: Groups -->
    <div class="column groups">
      <h4>Groups ({groups.length})</h4>
      <div class="list">
        {#each groups as group}
          <div
            class="item"
            class:selected={selectedGroup?.prefix === group.prefix}
            onclick={() => selectGroup(group)}
            role="button"
            tabindex="0"
            onkeydown={(e) => {
              if (e.key === 'Enter' || e.key === ' ') {
                e.preventDefault();
                selectGroup(group);
              }
            }}
          >
            <span class="name">{group.displayName}</span>
            <span class="count">{group.images.length}</span>
          </div>
        {/each}
      </div>
    </div>

    <!-- Column 2: Files in selected group -->
    <div class="column files">
      <h4>
        {selectedGroup?.displayName || 'Files'}
        ({selectedGroup?.images.length || 0})
      </h4>
      <div class="list">
        {#if selectedGroup}
          {#each selectedGroup.images as img, idx}
            <div
              class="item"
              class:selected={selectedImage?.name === img.name}
              onclick={() => selectImage(img, idx)}
              role="button"
              tabindex="0"
              onkeydown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  selectImage(img, idx);
                }
              }}
            >
              <span class="name">{img.name}</span>
              <span class="dim">{img.width}x{img.height}</span>
            </div>
          {/each}
        {:else}
          <div class="empty-msg">Select a group to view files</div>
        {/if}
      </div>
    </div>

    <!-- Column 3: Replacement preview and actions -->
    <div class="column replace"
         ondrop={handleDrop}
         ondragover={handleDragOver}
         role="region"
         aria-label="Replacement preview and file drop zone">

      <div class="replace-header">
        <h4>Replace</h4>
        <button onclick={() => fileInput.click()}>Load Files...</button>
        <input
            type="file"
            multiple
            accept="image/*,video/*"
            hidden
            bind:this={fileInput}
            onchange={handleFileSelect}
        />
      </div>

      <div class="replace-content">
        {#if isExtracting}
          <div class="empty-msg extracting">
            <p>Extracting frames from video...</p>
            <progress></progress>
          </div>
        {:else if !selectedImage}
          <div class="empty-msg">Select an image to replace</div>
        {:else if sourceFiles.length === 0}
          <div class="empty-msg drop-zone">
            <p>Drop images or video here</p>
            <p class="hint">or click "Load Files..." above</p>
          </div>
        {:else}
          <div class="preview-panel">
            <div class="preview-info">
              <div class="target-info">
                <span class="label">Target:</span>
                <span class="value">{selectedImage.name}</span>
                <span class="dim">{selectedImage.width}x{selectedImage.height}</span>
              </div>
              <div class="source-info">
                <span class="label">Source:</span>
                <span class="value">{sourceFiles[currentSourceIndex]?.name || '--'}</span>
                <span class="size">{sourceFiles[currentSourceIndex]
                  ? ((sourceFiles[currentSourceIndex].size / 1024).toFixed(1) + ' KB')
                  : '--'}</span>
              </div>
            </div>

            <div class="preview-image">
              {#if previewUrl}
                <img src={previewUrl} alt="Preview" />
              {:else}
                <div class="no-preview">No preview available</div>
              {/if}
            </div>

            <div class="navigation">
              <button onclick={prevImage} disabled={currentSourceIndex === 0}>
                &lt; Prev
              </button>
              <span class="position">
                {currentSourceIndex + 1} / {selectedGroup?.images.length || 0}
              </span>
              <button onclick={nextImage} disabled={currentSourceIndex >= (selectedGroup?.images.length || 0) - 1}>
                Next &gt;
              </button>
            </div>

            <div class="mapping-status">
              Mapped: {Math.min(sourceFiles.length, selectedGroup?.images.length || 0)} / {selectedGroup?.images.length || 0}
            </div>
          </div>
        {/if}
      </div>
    </div>
  </div>

  <div class="footer">
    <div class="buttons">
      <button onclick={onCancel}>Cancel</button>
      <button
        onclick={apply}
        disabled={!selectedGroup || sourceFiles.length === 0}
        class="primary"
      >
        Apply ({selectedGroup?.images.length || 0} images)
      </button>
    </div>
  </div>
</div>

<style>
  .sequence-replacer {
    display: flex;
    flex-direction: column;
    height: 100%;
    padding: 8px;
    box-sizing: border-box;
    background-color: #c0c0c0;
  }

  .header h3 { margin: 0; font-size: 16px; }
  .header p { margin: 4px 0 8px; font-size: 12px; }

  .content {
    display: flex;
    flex: 1;
    gap: 8px;
    overflow: hidden;
    margin-bottom: 8px;
  }

  .column {
    flex: 1;
    display: flex;
    flex-direction: column;
    background-color: #ffffff;
    border: 2px inset #ffffff;
    border-right-color: #dfdfdf;
    border-bottom-color: #dfdfdf;
    min-width: 0;
  }

  .column h4 {
    margin: 0;
    padding: 4px;
    background-color: #000080;
    color: white;
    font-size: 12px;
  }

  .list {
    flex: 1;
    overflow-y: auto;
    padding: 2px;
    font-family: monospace;
    font-size: 12px;
  }

  .item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 4px 6px;
    border-bottom: 1px dotted #ccc;
    cursor: pointer;
    user-select: none;
  }

  .item:hover {
    background-color: #e0e0ff;
  }

  .item.selected {
    background-color: #000080;
    color: white;
  }

  .name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
  }

  .dim, .count, .size {
    color: #666;
    font-size: 10px;
    margin-left: 8px;
    flex-shrink: 0;
  }

  .item.selected .dim, .item.selected .count {
    color: #ccc;
  }

  .replace-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background-color: #000080;
    padding-right: 2px;
  }

  .replace-header button {
    font-size: 10px;
    padding: 2px 6px;
    height: 20px;
  }

  .replace-content {
    flex: 1;
    overflow-y: auto;
    padding: 4px;
  }

  .empty-msg {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: #666;
    border: 2px dashed #999;
    margin: 4px;
    text-align: center;
  }

  .drop-zone {
    cursor: copy;
  }

  .drop-zone:hover {
    background-color: #e0ffe0;
    border-color: #008000;
  }

  .hint {
    font-size: 10px;
    color: #999;
  }

  .preview-panel {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .preview-info {
    display: flex;
    flex-direction: column;
    gap: 4px;
    font-size: 11px;
  }

  .target-info, .source-info {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 4px;
    background-color: #f0f0f0;
    border: 1px inset #ffffff;
  }

  .label {
    font-weight: bold;
    color: #000080;
    min-width: 50px;
  }

  .value {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .preview-image {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 150px;
    background-color: #e0e0e0;
    border: 2px inset #ffffff;
    padding: 8px;
  }

  .preview-image img {
    max-width: 100%;
    max-height: 200px;
    image-rendering: pixelated;
    object-fit: contain;
  }

  .no-preview {
    color: #999;
    font-size: 11px;
  }

  .navigation {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 12px;
  }

  .navigation button {
    min-width: 60px;
    height: 24px;
    font-size: 11px;
  }

  .position {
    font-size: 11px;
    font-family: monospace;
    min-width: 60px;
    text-align: center;
  }

  .mapping-status {
    text-align: center;
    font-size: 11px;
    padding: 4px;
    background-color: #f0f0f0;
    border: 1px inset #ffffff;
  }

  .footer {
    flex-shrink: 0;
  }

  .buttons {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }

  button {
    min-width: 70px;
    height: 24px;
  }

  button.primary {
    font-weight: bold;
  }

  button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
