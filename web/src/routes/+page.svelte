<script lang="ts">
	// Start a run. The form follows KERN's form guide (create_input_form): every field has a visible label and a hint,
	// errors appear above the field and are announced, numbers use inputmode="numeric", and there is one primary
	// button. Validation runs on submit only, so nobody is told off while they are still typing.
	import { goto } from '$app/navigation';
	import { api, type RunMeta, type ServerConfig } from '#lib/api.ts';
	import Alert from '#lib/components/Alert.svelte';
	import Badge from '#lib/components/Badge.svelte';
	import { i18n, type Locale } from '#lib/i18n.svelte.ts';
	import { STAGES } from '#lib/run.svelte.ts';
	import { onMount } from 'svelte';

	const { t } = i18n;

	let config = $state<ServerConfig | null>(null);
	let recent = $state<RunMeta[]>([]);

	let idea = $state('');
	let workItemKey = $state('DEMO-123');
	let maxQuestions = $state('6');
	let maxReviewRounds = $state('2');
	let language = $state<Locale>(i18n.locale);
	let languageTouched = false;
	let autoAnswer = $state(false);

	let errors = $state<Record<string, string>>({});
	let failure = $state<string | null>(null);
	let starting = $state(false);

	// The agents' language follows the UI language until someone picks one on purpose.
	$effect(() => {
		const locale = i18n.locale;
		if (!languageTouched) language = locale;
	});

	onMount(async () => {
		try {
			[config, recent] = await Promise.all([api.config(), api.runs()]);
			workItemKey = config.defaults.workItemKey;
			maxQuestions = String(config.defaults.maxQuestions);
			maxReviewRounds = String(config.defaults.maxReviewRounds);
		} catch (e) {
			failure = t('error.generic', { message: (e as Error).message });
		}
	});

	const qLimits = $derived(config?.limits.max_questions ?? [1, 20]);
	const rLimits = $derived(config?.limits.max_review_rounds ?? [1, 5]);

	function validate() {
		const next: Record<string, string> = {};
		if (idea.trim().length < 3) next.idea = t('home.idea.error');
		if (!/^[A-Za-z0-9_-]*$/.test(workItemKey.trim())) next.workItemKey = t('home.workItem.error');
		const inRange = (v: string, [min, max]: number[]) => /^\d+$/.test(v) && +v >= min && +v <= max;
		if (!inRange(maxQuestions, qLimits)) next.maxQuestions = t('home.number.error', { min: qLimits[0], max: qLimits[1] });
		if (!inRange(maxReviewRounds, rLimits))
			next.maxReviewRounds = t('home.number.error', { min: rLimits[0], max: rLimits[1] });
		errors = next;
		return Object.keys(next);
	}

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		failure = null;
		const invalid = validate();
		if (invalid.length) {
			document.getElementById(invalid[0])?.focus();
			return;
		}
		starting = true;
		try {
			const run = await api.start({
				idea: idea.trim(),
				workItemKey: workItemKey.trim(),
				maxQuestions: +maxQuestions,
				maxReviewRounds: +maxReviewRounds,
				language,
				autoAnswer
			});
			await goto(`/runs/${run.id}`);
		} catch (err) {
			failure = t('error.generic', { message: (err as Error).message });
			starting = false;
		}
	}

	const statusTone = { running: 'info', waiting: 'warning', done: 'success', failed: 'danger', cancelled: 'danger', interrupted: 'warning' } as const;
	const describedBy = (id: string) => (errors[id] ? `${id}-hint ${id}-error` : `${id}-hint`);
</script>

<svelte:head><title>{t('nav.new')} · {t('app.name')}</title></svelte:head>

<div class="kern-stack-xl">
	<section class="dp-hero kern-stack-md">
		<h1 class="kern-heading-x-large">{t('home.title')}</h1>
		<p class="kern-body kern-body--large">{t('home.lead')}</p>
	</section>

	<div class="kern-grid kern-grid-cols-1 kern-grid-cols-12-md kern-gap-xl">
		<div class="kern-col-7-md kern-stack-lg">
			{#if Object.keys(errors).length}
				<div class="kern-alert kern-alert--danger" role="alert">
					<div class="kern-alert__header">
						<span class="kern-icon kern-icon--danger" aria-hidden="true"></span>
						<span class="kern-title">{t('form.errors')}</span>
					</div>
					<div class="kern-alert__body">
						<ul class="kern-list">
							{#each Object.entries(errors) as [id, message] (id)}
								<li><a class="kern-link" href="#{id}">{message}</a></li>
							{/each}
						</ul>
					</div>
				</div>
			{/if}

			<form class="dp-panel kern-stack-lg" novalidate onsubmit={submit}>
				<div class="kern-form-input" class:kern-form-input--error={errors.idea}>
					<label class="kern-label kern-label--large" for="idea">{t('home.idea')}</label>
					<div class="kern-hint" id="idea-hint">{t('home.idea.hint')}</div>
					{#if errors.idea}
						<p class="kern-error" id="idea-error" role="alert">
							<span class="kern-icon kern-icon--danger" aria-hidden="true"></span><span class="kern-body">{errors.idea}</span>
						</p>
					{/if}
					<textarea
						class="kern-form-input__input"
						class:kern-form-input__input--error={errors.idea}
						id="idea"
						name="idea"
						rows="3"
						required
						aria-invalid={errors.idea ? true : undefined}
						aria-describedby={describedBy('idea')}
						bind:value={idea}
					></textarea>
				</div>

				<fieldset class="kern-fieldset">
					<legend class="kern-label">{t('home.settings')}</legend>
					<div class="kern-fieldset__body kern-stack-md">
						<div class="kern-grid kern-grid-cols-1 kern-grid-cols-2-md kern-gap-lg">
							<div class="kern-form-input" class:kern-form-input--error={errors.workItemKey}>
								<label class="kern-label" for="workItemKey">{t('home.workItem')}</label>
								<div class="kern-hint" id="workItemKey-hint">{t('home.workItem.hint')}</div>
								{#if errors.workItemKey}
									<p class="kern-error" id="workItemKey-error" role="alert">
										<span class="kern-icon kern-icon--danger" aria-hidden="true"></span><span class="kern-body">{errors.workItemKey}</span>
									</p>
								{/if}
								<input
									class="kern-form-input__input"
									class:kern-form-input__input--error={errors.workItemKey}
									id="workItemKey"
									name="workItemKey"
									type="text"
									autocomplete="off"
									spellcheck="false"
									aria-describedby={describedBy('workItemKey')}
									bind:value={workItemKey}
								/>
							</div>
							<div class="kern-form-input">
								<label class="kern-label" for="language">{t('home.agentLanguage')}</label>
								<div class="kern-hint" id="language-hint">{t('home.agentLanguage.hint')}</div>
								<div class="kern-form-input__select-wrapper">
									<select
										class="kern-form-input__select"
										id="language"
										name="language"
										aria-describedby="language-hint"
										bind:value={language}
										onchange={() => (languageTouched = true)}
									>
										<option value="en">{t('lang.en')}</option>
										<option value="de">{t('lang.de')}</option>
									</select>
								</div>
							</div>
							<div class="kern-form-input" class:kern-form-input--error={errors.maxQuestions}>
								<label class="kern-label" for="maxQuestions">{t('home.maxQuestions')}</label>
								<div class="kern-hint" id="maxQuestions-hint">{t('home.maxQuestions.hint', { min: qLimits[0], max: qLimits[1] })}</div>
								{#if errors.maxQuestions}
									<p class="kern-error" id="maxQuestions-error" role="alert">
										<span class="kern-icon kern-icon--danger" aria-hidden="true"></span><span class="kern-body">{errors.maxQuestions}</span>
									</p>
								{/if}
								<input
									class="kern-form-input__input kern-form-input__input--width-4"
									class:kern-form-input__input--error={errors.maxQuestions}
									id="maxQuestions"
									name="maxQuestions"
									type="text"
									inputmode="numeric"
									pattern="[0-9]*"
									aria-describedby={describedBy('maxQuestions')}
									bind:value={maxQuestions}
								/>
							</div>
							<div class="kern-form-input" class:kern-form-input--error={errors.maxReviewRounds}>
								<label class="kern-label" for="maxReviewRounds">{t('home.maxRounds')}</label>
								<div class="kern-hint" id="maxReviewRounds-hint">{t('home.maxRounds.hint', { min: rLimits[0], max: rLimits[1] })}</div>
								{#if errors.maxReviewRounds}
									<p class="kern-error" id="maxReviewRounds-error" role="alert">
										<span class="kern-icon kern-icon--danger" aria-hidden="true"></span><span class="kern-body">{errors.maxReviewRounds}</span>
									</p>
								{/if}
								<input
									class="kern-form-input__input kern-form-input__input--width-4"
									class:kern-form-input__input--error={errors.maxReviewRounds}
									id="maxReviewRounds"
									name="maxReviewRounds"
									type="text"
									inputmode="numeric"
									pattern="[0-9]*"
									aria-describedby={describedBy('maxReviewRounds')}
									bind:value={maxReviewRounds}
								/>
							</div>
						</div>
						<div class="kern-form-check">
							<input class="kern-form-check__checkbox" id="autoAnswer" name="autoAnswer" type="checkbox" aria-describedby="autoAnswer-hint" bind:checked={autoAnswer} />
							<label class="kern-label" for="autoAnswer">{t('home.auto')}</label>
						</div>
						<div class="kern-hint" id="autoAnswer-hint">{t('home.auto.hint')}</div>
					</div>
				</fieldset>

				{#if failure}
					<Alert tone="danger" title={failure} />
				{/if}

				<div>
					<button type="submit" class="kern-btn kern-btn--primary kern-btn--large" disabled={starting}>
						<span class="kern-label">{starting ? t('home.starting') : t('home.start')}</span>
						<span class="kern-icon kern-icon--arrow-forward" aria-hidden="true"></span>
					</button>
				</div>
			</form>
		</div>

		<aside class="kern-col-5-md kern-stack-lg" aria-labelledby="how-title">
			<div class="dp-sheet kern-stack-lg">
				<h2 class="kern-heading-medium" id="how-title">{t('home.how')}</h2>
				<ol class="kern-stack-md" style="list-style: none; margin: 0; padding: 0">
					{#each STAGES as stage, i (stage)}
						<li class="dp-step" class:dp-step--human={stage === 'approval'}>
							<span class="dp-step__number" aria-hidden="true">{i + 1}</span>
							<div class="kern-stack-xxs">
								<p class="kern-body kern-body--bold">{t(`stage.${stage}`)}</p>
								<p class="kern-body kern-body--small kern-body--muted">{t(`stage.${stage}.text`)}</p>
							</div>
						</li>
					{/each}
				</ol>
			</div>
			{#if config?.provider === 'mock'}
				<Alert tone="info" title={t('footer.mock')} role="status">
					<p class="kern-body kern-body--small">{t('home.mockNote')}</p>
				</Alert>
			{/if}
		</aside>
	</div>

	{#if recent.length}
		<section class="kern-stack-md" aria-labelledby="recent-title">
			<div class="kern-flex kern-justify-content-between kern-align-items-center kern-gap-md kern-flex-wrap">
				<h2 class="kern-heading-medium" id="recent-title">{t('home.recent')}</h2>
				<a class="kern-link" href="/runs">{t('home.allRuns')}<span class="kern-icon kern-icon--arrow-forward kern-icon--small" aria-hidden="true"></span></a>
			</div>
			<div class="kern-grid kern-grid-cols-1 kern-grid-cols-3-md kern-gap-lg">
				{#each recent.slice(0, 3) as run (run.id)}
					<article class="kern-card">
						<div class="kern-card__container">
							<header class="kern-card__header">
								<hgroup>
									<p class="kern-preline">{run.options.workItemKey} · {i18n.date(run.createdAt)}</p>
									<h3 class="kern-title"><a class="kern-link" href="/runs/{run.id}">{run.title ?? run.options.idea}</a></h3>
								</hgroup>
							</header>
							<section class="kern-card__body kern-stack-sm">
								<p class="kern-body kern-body--small kern-body--muted dp-ellipsis">{run.options.idea}</p>
								<div><Badge tone={statusTone[run.status]} text={t(`run.status.${run.status}`)} icon /></div>
							</section>
						</div>
					</article>
				{/each}
			</div>
		</section>
	{/if}
</div>
