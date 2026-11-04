<script lang="ts">
	// One KERN accordion per review round (get_accordion), the latest open; findings in a KERN table (get_table).
	import type { ReviewOutcome, Severity } from '#lib/api.ts';
	import { i18n } from '#lib/i18n.svelte.ts';
	import Badge from './Badge.svelte';

	let { reviews }: { reviews: ReviewOutcome[] } = $props();
	const { t } = i18n;

	const severityTone: Record<Severity, 'danger' | 'warning' | 'info'> = { High: 'danger', Medium: 'warning', Low: 'info' };
</script>

<div class="kern-stack-sm">
	{#each reviews as review, i (review.round)}
		<details class="kern-accordion" open={i === reviews.length - 1}>
			<summary class="kern-accordion__header">
				<span class="kern-title">
					{t('reviews.round', { n: review.round })}
					<span class="dp-summary-badges">
						<Badge
							tone={review.report.verdict === 'Approved' ? 'success' : 'warning'}
							text={t(`verdict.${review.report.verdict}`)}
							icon
						/>
						<Badge tone="info" text="{t('reviews.next')}: {t(`next.${review.next}`)}" />
					</span>
				</span>
			</summary>
			<section class="kern-accordion__body kern-stack-md">
				<p class="kern-body">{review.report.summary}</p>
				{#if review.report.findings.length === 0}
					<p class="kern-body kern-body--muted">{t('reviews.noFindings')}</p>
				{:else}
					<!-- svelte-ignore a11y_no_noninteractive_tabindex (KERN: the scrolling region must be keyboard-reachable) -->
					<div class="kern-table-responsive" tabindex="0" role="region" aria-labelledby="findings-{review.round}">
						<table class="kern-table">
							<caption class="kern-title" id="findings-{review.round}">{t('reviews.findings')}</caption>
							<thead class="kern-table__head">
								<tr class="kern-table__row">
									<th scope="col" class="kern-table__header">{t('reviews.severity')}</th>
									<th scope="col" class="kern-table__header">{t('reviews.file')}</th>
									<th scope="col" class="kern-table__header">{t('reviews.finding')}</th>
								</tr>
							</thead>
							<tbody class="kern-table__body">
								{#each review.report.findings as finding, j (j)}
									<tr class="kern-table__row">
										<td class="kern-table__cell"><Badge tone={severityTone[finding.severity]} text={t(`severity.${finding.severity}`)} /></td>
										<td class="kern-table__cell"><code>{finding.file}</code></td>
										<td class="kern-table__cell">{finding.message}</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}
				{#if review.report.testsWritten.length}
					<p class="kern-body kern-body--small kern-body--muted">
						{t('reviews.tests')}: {#each review.report.testsWritten as test, k (test)}{k ? ', ' : ''}<code>{test}</code>{/each}
					</p>
				{/if}
			</section>
		</details>
	{/each}
</div>
