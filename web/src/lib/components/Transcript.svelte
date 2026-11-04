<script lang="ts">
	// The interview so far: each question with its answer, and each spec decision with its reason.
	import type { RunEvent } from '#lib/api.ts';
	import { i18n } from '#lib/i18n.svelte.ts';
	import Badge from './Badge.svelte';

	type Ask = Extract<RunEvent, { kind: 'question' | 'approval' }>;
	type Answer = Extract<RunEvent, { kind: 'answered' }>;
	let { items }: { items: { ask: Ask; answer?: Answer }[] } = $props();
	const { t } = i18n;
</script>

{#if items.length === 0}
	<p class="kern-body kern-body--muted">{t('interview.empty')}</p>
{:else}
	<ol class="dp-transcript">
		{#each items as { ask, answer } (ask.requestId)}
			<li class="dp-transcript__item">
				{#if ask.kind === 'question'}
					<p class="kern-body kern-body--bold">
						<span class="dp-transcript__number">{ask.question.number}</span>{ask.question.question}
					</p>
					{#if answer}
						<p class="kern-body dp-transcript__answer">
							<span class="kern-sr-only">{t('interview.you')}: </span>
							{#if answer.response.endInterview}<em>{t('interview.ended')}</em>{:else}{answer.response.text}{/if}
							{#if answer.auto}<span class="kern-body--muted"> ({t('interview.auto')})</span>{/if}
						</p>
					{/if}
				{:else}
					<p class="kern-body kern-body--bold">{t('event.approval')}: {ask.spec.title}</p>
					{#if answer}
						<p class="kern-body dp-transcript__answer">
							<Badge
								tone={answer.response.approved ? 'success' : 'warning'}
								text={answer.response.approved ? t('interview.approved') : t('interview.rejected')}
								icon
							/>
							{#if answer.response.reason}<span> “{answer.response.reason}”</span>{/if}
						</p>
					{/if}
				{/if}
			</li>
		{/each}
	</ol>
{/if}
