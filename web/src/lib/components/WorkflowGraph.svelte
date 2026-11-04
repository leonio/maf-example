<script lang="ts">
	// The workflow graph as Agent Framework describes it (WorkflowViz.to_mermaid, saved as workflow.mmd). Mermaid is
	// large, so it is loaded only when this disclosure is first opened; if it cannot render, the source is shown.
	import { api } from '#lib/api.ts';
	import { i18n } from '#lib/i18n.svelte.ts';

	let { runId }: { runId: string } = $props();
	const { t } = i18n;

	let source = $state<string | null>(null);
	let svg = $state<string | null>(null);
	let loaded = false;

	async function load() {
		if (loaded) return;
		loaded = true;
		try {
			const text = await api.artifact(runId, 'workflow.mmd');
			source = text;
			const { default: mermaid } = await import('mermaid');
			const dark = matchMedia('(prefers-color-scheme: dark)').matches;
			mermaid.initialize({ startOnLoad: false, theme: dark ? 'dark' : 'neutral', securityLevel: 'strict' });
			svg = (await mermaid.render(`workflow-${Math.random().toString(36).slice(2)}`, text)).svg;
		} catch {
			svg = null; // fall back to the source text
		}
	}
</script>

<details class="kern-accordion" ontoggle={(e) => (e.currentTarget as HTMLDetailsElement).open && load()}>
	<summary class="kern-accordion__header">
		<span class="kern-title">{t('workflow.title')}</span>
	</summary>
	<section class="kern-accordion__body kern-stack-md">
		<p class="kern-body kern-body--muted">{t('workflow.lead')}</p>
		{#if svg}
			<div class="dp-graph">{@html svg}</div>
		{:else if source}
			<pre class="dp-code"><code>{source}</code></pre>
		{:else}
			<div class="kern-loader kern-loader--visible" role="status"><span class="kern-sr-only">{t('run.loading')}</span></div>
		{/if}
	</section>
</details>
