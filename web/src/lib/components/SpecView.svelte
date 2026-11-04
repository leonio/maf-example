<script lang="ts">
	// The spec, rendered from its structured form: a KERN description list for the facts, KERN lists for the rest.
	import type { Spec } from '#lib/api.ts';
	import { i18n } from '#lib/i18n.svelte.ts';

	let { spec, headingLevel = 3 }: { spec: Spec; headingLevel?: 2 | 3 } = $props();
	const { t } = i18n;

	const sections = $derived([
		{ key: 'spec.userStories', items: spec.userStories, ordered: false },
		{ key: 'spec.acceptance', items: spec.acceptanceCriteria, ordered: true },
		{ key: 'spec.assumptions', items: spec.assumptions, ordered: false },
		{ key: 'spec.outOfScope', items: spec.outOfScope, ordered: false }
	] as const);

	// Model text may contain `code` spans; show them as code, everything else as plain text (no HTML from models).
	function parts(text: string) {
		return text.split(/(`[^`]+`)/g).map((p) => (p.startsWith('`') && p.endsWith('`') ? { code: p.slice(1, -1) } : { text: p }));
	}
</script>

<div class="kern-stack-lg dp-spec">
	<div class="kern-stack-sm">
		<svelte:element this={`h${headingLevel}`} class="kern-heading-small">{spec.title}</svelte:element>
		<p class="kern-body kern-body--large">{spec.summary}</p>
	</div>

	<dl class="kern-description-list">
		<div class="kern-description-list-item">
			<dt class="kern-description-list-item__key">{t('spec.primaryUser')}</dt>
			<dd class="kern-description-list-item__value">{spec.primaryUser}</dd>
		</div>
		<div class="kern-description-list-item">
			<dt class="kern-description-list-item__key">{t('spec.appKind')}</dt>
			<dd class="kern-description-list-item__value"><code>{spec.appKind}</code></dd>
		</div>
	</dl>

	{#each sections as section (section.key)}
		<section class="kern-stack-xs">
			<svelte:element this={`h${headingLevel + 1}`} class="kern-title">{t(section.key)}</svelte:element>
			{#if section.items.length === 0}
				<p class="kern-body kern-body--muted">{t('spec.none')}</p>
			{:else}
				<svelte:element this={section.ordered ? 'ol' : 'ul'} class="kern-list {section.ordered ? 'kern-list--number' : 'kern-list--bullet'}">
					{#each section.items as item, i (i)}
						<li>
							{#each parts(item) as part, j (j)}{#if 'code' in part}<code>{part.code}</code>{:else}{part.text}{/if}{/each}
						</li>
					{/each}
				</svelte:element>
			{/if}
		</section>
	{/each}
</div>
