<script lang="ts">
	// KERN Badge: a short, non-interactive status label in one of four tones (markup from the kern-ux MCP server's
	// get_badge).
	type Tone = 'info' | 'success' | 'warning' | 'danger';
	let { tone = 'info', text, icon = false }: { tone?: Tone; text: string; icon?: boolean } = $props();
</script>

<span class="kern-badge kern-badge--{tone}">
	{#if icon}<span class="kern-icon kern-icon--{tone}" aria-hidden="true"></span>{/if}
	<span class="kern-label kern-label--small">{text}</span>
</span>
