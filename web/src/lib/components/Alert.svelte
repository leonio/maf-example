<script lang="ts">
	// KERN Alert (get_alert): a heading with a status icon and an optional body. role="alert" is for things that
	// just happened; a standing notice passes role="status" so screen readers do not interrupt.
	import type { Snippet } from 'svelte';

	type Tone = 'info' | 'success' | 'warning' | 'danger';
	let {
		tone = 'info',
		title,
		role = 'alert',
		children
	}: { tone?: Tone; title: string; role?: 'alert' | 'status'; children?: Snippet } = $props();
</script>

<div class="kern-alert kern-alert--{tone}" {role}>
	<div class="kern-alert__header">
		<span class="kern-icon kern-icon--{tone}" aria-hidden="true"></span>
		<span class="kern-title">{title}</span>
	</div>
	{#if children}
		<div class="kern-alert__body">{@render children()}</div>
	{/if}
</div>
