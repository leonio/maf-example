<script lang="ts">
	// The workflow's output: the merge request. The body is Markdown written by the model, rendered to HTML on the
	// server with raw HTML disabled, so it cannot inject markup into the page.
	import type { MergeRequestPlan } from '#lib/api.ts';
	import { i18n } from '#lib/i18n.svelte.ts';
	import Alert from './Alert.svelte';

	let { plan, runId, downloadUrl }: { plan: MergeRequestPlan; runId: string; downloadUrl: string } = $props();
	const { t } = i18n;
	let copied = $state(false);

	async function copy() {
		try {
			await navigator.clipboard.writeText(plan.commands.join('\n'));
			copied = true;
			setTimeout(() => (copied = false), 2000);
		} catch {
			// clipboard blocked: the commands are selectable anyway
		}
	}
</script>

<section class="dp-panel dp-panel--result kern-stack-lg" aria-labelledby="result-title">
	<Alert tone="success" title={t('result.title')} role="status">
		<p class="kern-body">{t('result.lead')}</p>
	</Alert>

	<div class="kern-stack-sm">
		<p class="kern-preline">{t('stage.release')}</p>
		<h2 class="kern-heading-medium" id="result-title">{plan.title}</h2>
	</div>

	<dl class="kern-description-list">
		<div class="kern-description-list-item">
			<dt class="kern-description-list-item__key">{t('result.branch')}</dt>
			<dd class="kern-description-list-item__value"><code>{plan.branch}</code></dd>
		</div>
		<div class="kern-description-list-item">
			<dt class="kern-description-list-item__key">{t('result.pr')}</dt>
			<dd class="kern-description-list-item__value">
				{#if plan.pullRequestUrl}
					<a class="kern-link" href={plan.pullRequestUrl} target="_blank" rel="noreferrer noopener">
						{plan.pullRequestUrl}<span class="kern-icon kern-icon--open-in-new kern-icon--small" aria-hidden="true"></span>
					</a>
				{:else}{t('result.prNone')}{/if}
			</dd>
		</div>
	</dl>

	<div class="dp-sheet dp-markdown">{@html plan.bodyHtml}</div>

	<div class="kern-stack-sm">
		<div class="kern-flex kern-justify-content-between kern-gap-md kern-flex-wrap">
			<h3 class="kern-title">{t('result.commands')}</h3>
			<button type="button" class="kern-btn kern-btn--tertiary kern-btn--small" onclick={copy}>
				<span class="kern-icon kern-icon--{copied ? 'check' : 'content-copy'}" aria-hidden="true"></span>
				<span class="kern-label">{copied ? t('result.copied') : t('result.copy')}</span>
			</button>
		</div>
		<pre class="dp-code"><code>{plan.commands.join('\n')}</code></pre>
	</div>

	{#if plan.notes.length}
		<div class="kern-stack-xs">
			<h3 class="kern-title">{t('result.notes')}</h3>
			<ul class="kern-list kern-list--bullet">
				{#each plan.notes as note, i (i)}<li>{note}</li>{/each}
			</ul>
		</div>
	{/if}

	<div>
		<a class="kern-btn kern-btn--secondary" href={downloadUrl} download="{runId}.zip">
			<span class="kern-icon kern-icon--download" aria-hidden="true"></span>
			<span class="kern-label">{t('run.download')}</span>
		</a>
	</div>
</section>
