<script lang="ts">
	// One run, live. What needs the human comes first (a question or the spec approval), then the result, then the
	// record: reviews, the interview, the generated app, the activity log and the workflow graph. The sidebar shows
	// where the run is.
	import { page } from '$app/state';
	import { api } from '#lib/api.ts';
	import Alert from '#lib/components/Alert.svelte';
	import ApprovalForm from '#lib/components/ApprovalForm.svelte';
	import Badge from '#lib/components/Badge.svelte';
	import FileBrowser from '#lib/components/FileBrowser.svelte';
	import QuestionForm from '#lib/components/QuestionForm.svelte';
	import ResultPanel from '#lib/components/ResultPanel.svelte';
	import ReviewList from '#lib/components/ReviewList.svelte';
	import SpecView from '#lib/components/SpecView.svelte';
	import StageList from '#lib/components/StageList.svelte';
	import Timeline from '#lib/components/Timeline.svelte';
	import Transcript from '#lib/components/Transcript.svelte';
	import WorkflowGraph from '#lib/components/WorkflowGraph.svelte';
	import { i18n } from '#lib/i18n.svelte.ts';
	import { LiveRun } from '#lib/run.svelte.ts';

	const { t } = i18n;

	let run = $state<LiveRun | null>(null);
	$effect(() => {
		const live = new LiveRun(page.params.id ?? '');
		run = live;
		void live.load();
		return () => live.close();
	});

	const statusTone = { running: 'info', waiting: 'warning', done: 'success', failed: 'danger', cancelled: 'danger', interrupted: 'warning' } as const;

	async function cancel() {
		if (run?.detail && confirm(t('run.cancelConfirm'))) await api.cancel(run.detail.id);
	}
</script>

<svelte:head><title>{run?.detail?.title ?? run?.detail?.options.idea ?? '…'} · {t('app.name')}</title></svelte:head>

{#if !run || (!run.detail && !run.notFound && !run.error)}
	<div class="dp-hero"><div class="kern-loader kern-loader--visible" role="status"><span class="kern-sr-only">{t('run.loading')}</span></div></div>
{:else if run.notFound}
	<div class="dp-hero"><Alert tone="warning" title={t('run.notFound')}><p class="kern-body"><a class="kern-link" href="/runs">{t('home.allRuns')}</a></p></Alert></div>
{:else if run.error || !run.detail}
	<div class="dp-hero"><Alert tone="danger" title={t('error.generic', { message: run.error ?? '' })} /></div>
{:else}
	{@const detail = run.detail}
	{@const status = run.status ?? detail.status}
	{@const pending = run.pending}
	{@const result = run.result}
	{@const reviews = run.reviews}
	<div class="kern-stack-xl">
		<section class="dp-hero kern-stack-sm">
			<p class="kern-preline">{detail.options.workItemKey} · {i18n.date(detail.createdAt)}</p>
			<h1 class="kern-heading-x-large">{run.approvedSpec?.title ?? detail.title ?? detail.options.idea}</h1>
			<div class="kern-flex kern-flex-wrap kern-gap-sm kern-align-items-center">
				<Badge tone={statusTone[status]} text={t(`run.status.${status}`)} icon />
				{#if detail.title || run.approvedSpec}<p class="kern-body kern-body--muted">{detail.options.idea}</p>{/if}
			</div>
		</section>

		{#if !run.connected}
			<Alert tone="warning" title={t('run.connection')} role="status" />
		{/if}

		<div class="kern-grid kern-grid-cols-1 kern-grid-cols-12-lg kern-gap-xl">
			<div class="kern-col-8-lg kern-stack-xl" style="min-width: 0">
				{#if pending?.kind === 'question'}
					{#key pending.requestId}<QuestionForm runId={detail.id} requestId={pending.requestId} question={pending.question} />{/key}
				{:else if pending?.kind === 'approval'}
					{#key pending.requestId}<ApprovalForm runId={detail.id} requestId={pending.requestId} spec={pending.spec} />{/key}
				{:else if status === 'running'}
					<div class="dp-panel kern-flex kern-gap-md kern-align-items-center" role="status">
						<div class="kern-loader kern-loader--visible"><span class="kern-sr-only">{t('run.working')}</span></div>
						<p class="kern-body kern-body--large">{t('run.working')}</p>
					</div>
				{/if}

				{#if status === 'failed'}
					<Alert tone="danger" title={t('run.failed')}><p class="kern-body"><code>{run.failure}</code></p></Alert>
				{:else if status === 'cancelled'}
					<Alert tone="warning" title={t('run.cancelled')} role="status" />
				{:else if status === 'interrupted'}
					<Alert tone="warning" title={t('run.interrupted')} role="status"><p class="kern-body">{t('run.interrupted.text')}</p></Alert>
				{/if}

				{#if result}
					<ResultPanel plan={result} runId={detail.id} downloadUrl={api.downloadUrl(detail.id)} />
				{/if}

				{#if reviews.length}
					<section class="kern-stack-md" aria-labelledby="reviews-title">
						<h2 class="kern-heading-medium" id="reviews-title">{t('reviews.title')}</h2>
						<ReviewList {reviews} />
					</section>
				{/if}

				{#if run.approvedSpec}
					<details class="kern-accordion">
						<summary class="kern-accordion__header"><span class="kern-title">{t('spec.approved')}</span></summary>
						<section class="kern-accordion__body"><SpecView spec={run.approvedSpec} /></section>
					</details>
				{/if}

				<section class="kern-stack-md" aria-labelledby="interview-title">
					<h2 class="kern-heading-medium" id="interview-title">{t('interview.title')}</h2>
					<Transcript items={run.transcript} />
				</section>

				<section class="kern-stack-md" aria-labelledby="files-title">
					<h2 class="kern-heading-medium" id="files-title">{t('files.title')}</h2>
					<FileBrowser runId={detail.id} files={run.files} />
				</section>

				<section class="kern-stack-md" aria-labelledby="activity-title">
					<div class="kern-flex kern-justify-content-between kern-align-items-center kern-gap-md kern-flex-wrap">
						<h2 class="kern-heading-medium" id="activity-title">{t('activity.title')}</h2>
						<span class="kern-body kern-body--small kern-body--muted">{t('activity.count', { n: run.events.length })}</span>
					</div>
					<Timeline events={run.events} />
				</section>

				<WorkflowGraph runId={detail.id} />
			</div>

			<aside class="kern-col-4-lg">
				<div class="dp-sticky kern-stack-lg">
					<div class="dp-sheet"><StageList stages={run.stages} rounds={reviews.length} /></div>

					<div class="kern-stack-sm">
						<h2 class="kern-heading-small">{t('run.facts')}</h2>
						<dl class="kern-description-list dp-facts">
							<div class="kern-description-list-item">
								<dt class="kern-description-list-item__key">{t('run.language')}</dt>
								<dd class="kern-description-list-item__value">{t(`lang.${detail.options.language}`)}</dd>
							</div>
							<div class="kern-description-list-item">
								<dt class="kern-description-list-item__key">{t('run.budget')}</dt>
								<dd class="kern-description-list-item__value">{detail.options.maxQuestions}</dd>
							</div>
							<div class="kern-description-list-item">
								<dt class="kern-description-list-item__key">{t('run.rounds')}</dt>
								<dd class="kern-description-list-item__value">{reviews.length} / {detail.options.maxReviewRounds}</dd>
							</div>
							<div class="kern-description-list-item">
								<dt class="kern-description-list-item__key">{t('run.answering')}</dt>
								<dd class="kern-description-list-item__value">{detail.options.autoAnswer ? t('run.answering.auto') : t('run.answering.you')}</dd>
							</div>
						</dl>
					</div>

					<div class="kern-flex kern-flex-col kern-gap-sm">
						{#if run.files.length}
							<a class="kern-btn kern-btn--secondary" href={api.downloadUrl(detail.id)} download="{detail.id}.zip">
								<span class="kern-icon kern-icon--download" aria-hidden="true"></span>
								<span class="kern-label">{t('run.download')}</span>
							</a>
						{/if}
						{#if run.isActive}
							<button type="button" class="kern-btn kern-btn--tertiary" onclick={cancel}>
								<span class="kern-icon kern-icon--close" aria-hidden="true"></span>
								<span class="kern-label">{t('run.cancel')}</span>
							</button>
						{/if}
					</div>
				</div>
			</aside>
		</div>
	</div>
{/if}
