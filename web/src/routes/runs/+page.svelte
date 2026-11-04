<script lang="ts">
	// Every run on this server, newest first, in a KERN table (get_table) inside its scrolling region.
	import { api, type RunMeta } from '#lib/api.ts';
	import Alert from '#lib/components/Alert.svelte';
	import Badge from '#lib/components/Badge.svelte';
	import { i18n } from '#lib/i18n.svelte.ts';
	import { onMount } from 'svelte';

	const { t } = i18n;
	let runs = $state<RunMeta[] | null>(null);
	let failure = $state<string | null>(null);

	onMount(async () => {
		try {
			runs = await api.runs();
		} catch (e) {
			failure = t('error.generic', { message: (e as Error).message });
		}
	});

	const statusTone = { running: 'info', waiting: 'warning', done: 'success', failed: 'danger', cancelled: 'danger', interrupted: 'warning' } as const;
</script>

<svelte:head><title>{t('runs.title')} · {t('app.name')}</title></svelte:head>

<div class="kern-stack-lg dp-hero">
	<div class="kern-stack-sm">
		<h1 class="kern-heading-x-large">{t('runs.title')}</h1>
		<p class="kern-body kern-body--large">{t('runs.lead')}</p>
	</div>

	{#if failure}
		<Alert tone="danger" title={failure} />
	{:else if runs === null}
		<div class="kern-loader kern-loader--visible" role="status"><span class="kern-sr-only">{t('run.loading')}</span></div>
	{:else if runs.length === 0}
		<p class="kern-body">{t('runs.empty')} <a class="kern-link" href="/">{t('nav.new')}</a></p>
	{:else}
		<!-- svelte-ignore a11y_no_noninteractive_tabindex (KERN: the scrolling region must be keyboard-reachable) -->
		<div class="kern-table-responsive" tabindex="0" role="region" aria-labelledby="runs-caption">
			<table class="kern-table">
				<caption class="kern-title kern-sr-only" id="runs-caption">{t('runs.caption')}</caption>
				<thead class="kern-table__head">
					<tr class="kern-table__row">
						<th scope="col" class="kern-table__header">{t('runs.idea')}</th>
						<th scope="col" class="kern-table__header">{t('run.workItem')}</th>
						<th scope="col" class="kern-table__header">{t('runs.started')}</th>
						<th scope="col" class="kern-table__header">{t('runs.status')}</th>
						<th scope="col" class="kern-table__header">{t('runs.verdict')}</th>
						<th scope="col" class="kern-table__header kern-table__header--numeric">{t('runs.rounds')}</th>
					</tr>
				</thead>
				<tbody class="kern-table__body">
					{#each runs as run (run.id)}
						<tr class="kern-table__row">
							<th scope="row" class="kern-table__cell">
								<a class="kern-link" href="/runs/{run.id}">{run.title ?? run.options.idea}</a>
								{#if run.title}<span class="kern-body kern-body--small kern-body--muted" style="display:block">{run.options.idea}</span>{/if}
							</th>
							<td class="kern-table__cell"><code>{run.options.workItemKey}</code></td>
							<td class="kern-table__cell">{i18n.date(run.createdAt)}</td>
							<td class="kern-table__cell"><Badge tone={statusTone[run.status]} text={t(`run.status.${run.status}`)} icon /></td>
							<td class="kern-table__cell">{run.verdict ? t(`verdict.${run.verdict}`) : '–'}</td>
							<td class="kern-table__cell kern-table__cell--numeric">{run.rounds || '–'}</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
