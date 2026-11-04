<script lang="ts">
	// Everything that happened, newest last. Stage events are translated from their code; tool calls (the agents'
	// actual reads and writes) are hidden behind a checkbox because there are many of them.
	import type { RunEvent } from '#lib/api.ts';
	import { i18n } from '#lib/i18n.svelte.ts';

	let { events }: { events: RunEvent[] } = $props();
	const { t, tx } = i18n;
	let showTools = $state(true);

	function describe(e: RunEvent): string | null {
		switch (e.kind) {
			case 'started':
				return t('event.started', { provider: e.model ? `${e.provider} / ${e.model}` : e.provider });
			case 'stage': {
				const params = { ...e.params } as Record<string, unknown>;
				if (typeof params.verdict === 'string') params.verdict = tx(`verdict.${params.verdict}`);
				if (typeof params.next === 'string') params.next = tx(`next.${params.next}`);
				const key = e.code === 'develop.started' && params.round === 1 ? 'code.develop.started.first' : `code.${e.code}`;
				return tx(key, params, e.code);
			}
			case 'question':
				return t('event.question', { n: e.question.number, question: e.question.question });
			case 'approval':
				return t('event.approval');
			case 'review':
				return t('event.review', { n: e.review.round, verdict: tx(`verdict.${e.review.report.verdict}`) });
			case 'result':
				return t('event.result');
			case 'status':
				// "waiting" and "running again" just mirror the questions and answers already listed.
				return e.status === 'running' || e.status === 'waiting'
					? null
					: tx(`event.status.${e.status}`, { error: e.error ?? '' });
			default:
				return null;
		}
	}

	const shown = $derived(events.filter((e) => (e.kind === 'tool' ? showTools : e.kind !== 'answered' && describe(e) !== null)));
</script>

<div class="kern-stack-md">
	<div class="kern-form-check">
		<input class="kern-form-check__checkbox" id="show-tools" type="checkbox" bind:checked={showTools} />
		<label class="kern-label" for="show-tools">{t('activity.tools')}</label>
	</div>
	<ol class="dp-timeline" aria-live="off">
		{#each shown as e (e.seq)}
			<li class="dp-timeline__item dp-timeline__item--{e.kind}">
				<time class="dp-timeline__time" datetime={e.at}>{i18n.time(e.at)}</time>
				{#if e.kind === 'tool'}
					<span class="dp-timeline__tool">
						<span class="dp-agent dp-agent--{e.agent}">{e.agent}</span>
						<code>{e.tool}({e.arguments})</code>
						{#if e.result}<span class="dp-timeline__result">→ {e.result}</span>{/if}
					</span>
				{:else}
					<span class="dp-timeline__text">
						{describe(e)}
						{#if e.kind === 'stage' && e.detail}<span class="dp-timeline__detail">{e.detail}</span>{/if}
					</span>
				{/if}
			</li>
		{/each}
	</ol>
</div>
