<script lang="ts">
	// Where the run is, as a vertical stepper: one marker per stage joined by a line that fills in as stages finish,
	// the current stage's description underneath it, and a progress summary on top. Status is in text as well as
	// colour, and the current stage carries aria-current="step".
	import { i18n } from '#lib/i18n.svelte.ts';
	import { STAGES, type Stage, type StageState } from '#lib/run.svelte.ts';

	let { stages, rounds = 0 }: { stages: Record<Stage, StageState>; rounds?: number } = $props();
	const { t } = i18n;

	const done = $derived(STAGES.filter((s) => stages[s] === 'done').length);
</script>

<section class="dp-stepper" aria-labelledby="stages-title">
	<div class="dp-stepper__head">
		<h2 class="kern-heading-small" id="stages-title">{t('run.stages')}</h2>
		<span class="dp-stepper__count">{t('run.stagesDone', { done, total: STAGES.length })}</span>
	</div>
	<div class="dp-stepper__progress" aria-hidden="true">
		<span style="width: {(done / STAGES.length) * 100}%"></span>
	</div>

	<ol class="dp-stepper__list">
		{#each STAGES as stage, i (stage)}
			{@const state = stages[stage]}
			{@const current = state === 'active' || state === 'waiting'}
			<li class="dp-stepper__item is-{state}" aria-current={current ? 'step' : undefined}>
				<span class="dp-stepper__marker" aria-hidden="true">
					{#if state === 'done'}
						<span class="kern-icon kern-icon--check"></span>
					{:else if state === 'failed'}
						<span class="kern-icon kern-icon--close"></span>
					{:else}
						{i + 1}
					{/if}
				</span>
				<div class="dp-stepper__body">
					<p class="dp-stepper__title">{t(`stage.${stage}`)}</p>
					<p class="dp-stepper__status">
						{#if state === 'active'}<span class="dp-spinner" aria-hidden="true"></span>{/if}
						{t(`status.${state}`)}
						{#if (stage === 'develop' || stage === 'test') && rounds > 0 && state !== 'open'}
							<span class="dp-stepper__round">· {t('reviews.round', { n: rounds })}</span>
						{/if}
					</p>
					{#if current}
						<p class="dp-stepper__hint">{t(`stage.${stage}.text`)}</p>
					{/if}
				</div>
			</li>
		{/each}
	</ol>
</section>

<style>
	.dp-stepper {
		display: grid;
		gap: var(--kern-metric-space-default);
	}
	.dp-stepper__head {
		display: flex;
		align-items: baseline;
		justify-content: space-between;
		gap: var(--kern-metric-space-small);
	}
	.dp-stepper__count {
		color: var(--kern-color-layout-text-muted);
		font-size: 0.875rem;
		font-variant-numeric: tabular-nums;
	}
	.dp-stepper {
		--track: color-mix(in srgb, var(--kern-color-layout-border) 28%, transparent);
	}
	.dp-stepper__progress {
		height: 6px;
		border-radius: 999px;
		background: var(--track);
		overflow: hidden;
	}
	.dp-stepper__progress span {
		display: block;
		height: 100%;
		border-radius: inherit;
		background: var(--kern-color-feedback-success);
		transition: width 0.4s ease;
	}

	.dp-stepper__list {
		list-style: none;
		margin: var(--kern-metric-space-x-small) 0 0;
		padding: 0;
	}
	.dp-stepper__item {
		--marker: 2rem;
		position: relative;
		display: grid;
		grid-template-columns: var(--marker) 1fr;
		gap: 0.85rem;
		padding-bottom: 1.25rem;
	}
	.dp-stepper__item:last-child {
		padding-bottom: 0;
	}
	/* The line to the next marker. */
	.dp-stepper__item:not(:last-child)::before {
		content: '';
		position: absolute;
		left: calc(var(--marker) / 2 - 1px);
		top: calc(var(--marker) + 4px);
		bottom: 4px;
		width: 2px;
		border-radius: 2px;
		background: var(--track);
	}
	.dp-stepper__item.is-done:not(:last-child)::before {
		background: var(--kern-color-feedback-success);
	}

	.dp-stepper__marker {
		display: inline-grid;
		place-items: center;
		width: var(--marker);
		height: var(--marker);
		border-radius: 50%;
		border: 2px solid color-mix(in srgb, var(--kern-color-layout-border) 55%, transparent);
		background: var(--kern-color-layout-background-default);
		color: var(--kern-color-layout-text-muted);
		font-size: 0.875rem;
		font-weight: 700;
		font-variant-numeric: tabular-nums;
	}
	.dp-stepper__marker .kern-icon {
		margin: 0;
		width: 1.1rem;
		height: 1.1rem;
		min-width: 0;
		min-height: 0;
		background-color: currentColor !important;
	}
	.is-done .dp-stepper__marker {
		border-color: var(--kern-color-feedback-success);
		background: var(--kern-color-feedback-success);
		color: var(--kern-color-layout-background-default);
	}
	.is-active .dp-stepper__marker {
		border-color: var(--kern-color-action-default);
		color: var(--kern-color-action-default);
		box-shadow: 0 0 0 4px color-mix(in srgb, var(--kern-color-action-default) 18%, transparent);
	}
	.is-waiting .dp-stepper__marker {
		border-color: var(--kern-color-feedback-warning);
		background: var(--kern-color-feedback-warning-background);
		color: var(--kern-color-layout-text-default);
		box-shadow: 0 0 0 4px color-mix(in srgb, var(--kern-color-feedback-warning) 25%, transparent);
		animation: dp-pulse 1.8s ease-in-out infinite;
	}
	.is-failed .dp-stepper__marker {
		border-color: var(--kern-color-feedback-danger);
		background: var(--kern-color-feedback-danger);
		color: var(--kern-color-layout-background-default);
	}

	.dp-stepper__body {
		min-width: 0;
		padding-top: 0.2rem;
	}
	.dp-stepper__title {
		margin: 0;
		font-weight: 600;
		line-height: 1.3;
	}
	.is-open .dp-stepper__title {
		color: var(--kern-color-layout-text-muted);
		font-weight: 500;
	}
	.dp-stepper__status {
		display: flex;
		flex-wrap: wrap;
		align-items: center;
		gap: 0.35rem;
		margin: 0.15rem 0 0;
		font-size: 0.8125rem;
		color: var(--kern-color-layout-text-muted);
	}
	.is-done .dp-stepper__status {
		color: var(--kern-color-feedback-success);
		font-weight: 600;
	}
	.is-active .dp-stepper__status {
		color: var(--kern-color-action-default);
		font-weight: 600;
	}
	.is-waiting .dp-stepper__status {
		color: var(--kern-color-layout-text-default);
		font-weight: 700;
	}
	.is-failed .dp-stepper__status {
		color: var(--kern-color-feedback-danger);
		font-weight: 600;
	}
	.dp-stepper__round {
		color: var(--kern-color-layout-text-muted);
		font-weight: 400;
	}
	.dp-stepper__hint {
		margin: 0.4rem 0 0;
		font-size: 0.875rem;
		line-height: 1.45;
		color: var(--kern-color-layout-text-muted);
	}

	@keyframes dp-pulse {
		50% {
			box-shadow: 0 0 0 7px color-mix(in srgb, var(--kern-color-feedback-warning) 10%, transparent);
		}
	}
	@media (prefers-reduced-motion: reduce) {
		.is-waiting .dp-stepper__marker {
			animation: none;
		}
		.dp-stepper__progress span {
			transition: none;
		}
	}
</style>
