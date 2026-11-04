<script lang="ts">
	// One interview question. KERN radios (get_radio, mode 'list') for the suggestions plus "Something else" with a
	// KERN textarea, an error in KERN's error pattern, and the two actions: one primary button per page, as KERN asks.
	import { api, type Question } from '#lib/api.ts';
	import { i18n } from '#lib/i18n.svelte.ts';

	let { runId, requestId, question }: { runId: string; requestId: string; question: Question } = $props();
	const { t } = i18n;

	const OWN = '__own__';
	let choice = $state('');
	let own = $state('');
	let error = $state<string | null>(null);
	let sending = $state(false);
	let failure = $state<string | null>(null);

	const answer = $derived(choice === OWN ? own.trim() : choice);

	async function send(endInterview = false) {
		failure = null;
		if (!endInterview && !answer) {
			error = t('question.error');
			document.getElementById(choice === OWN ? 'own-answer' : 'suggestion-0')?.focus();
			return;
		}
		error = null;
		sending = true;
		try {
			await api.answer(runId, requestId, endInterview ? answer || '/done' : answer, endInterview);
		} catch (e) {
			failure = t('error.generic', { message: (e as Error).message });
			sending = false;
		}
	}
</script>

<section class="dp-panel dp-panel--action kern-stack-lg" aria-labelledby="question-title">
	<div class="kern-stack-xs">
		<p class="kern-preline">{t('stage.interview')}</p>
		<h2 class="kern-heading-medium" id="question-title">{t('question.title', { n: question.number, budget: question.budget })}</h2>
	</div>

	<div class="kern-stack-sm">
		<p class="kern-body kern-body--large dp-question">{question.question}</p>
		{#if question.why}
			<p class="kern-body kern-body--muted">
				<span class="kern-icon kern-icon--info kern-icon--small" aria-hidden="true"></span>
				<span class="kern-sr-only">{t('question.why')}: </span>{question.why}
			</p>
		{/if}
	</div>

	<form
		class="kern-stack-lg"
		novalidate
		onsubmit={(e) => {
			e.preventDefault();
			send();
		}}
	>
		<fieldset class="kern-fieldset" class:kern-fieldset--error={error} aria-describedby={error ? 'question-error' : undefined}>
			<legend class="kern-label">{t('question.suggestions')}</legend>
			{#if error}
				<p class="kern-error" id="question-error" role="alert">
					<span class="kern-icon kern-icon--danger" aria-hidden="true"></span>
					<span class="kern-body">{error}</span>
				</p>
			{/if}
			<div class="kern-fieldset__body">
				{#each question.suggestedAnswers as suggestion, i (i)}
					<div class="kern-form-check">
						<input class="kern-form-check__radio" id="suggestion-{i}" name="answer" type="radio" value={suggestion} bind:group={choice} />
						<label class="kern-label" for="suggestion-{i}">{suggestion}</label>
					</div>
				{/each}
				<div class="kern-form-check">
					<input class="kern-form-check__radio" id="suggestion-own" name="answer" type="radio" value={OWN} bind:group={choice} />
					<label class="kern-label" for="suggestion-own">{t('question.own.option')}</label>
				</div>
			</div>
		</fieldset>

		{#if choice === OWN}
			<div class="kern-form-input">
				<label class="kern-label" for="own-answer">{t('question.own')}</label>
				<div class="kern-hint" id="own-answer-hint">{t('question.own.hint')}</div>
				<!-- svelte-ignore a11y_autofocus -->
				<textarea class="kern-form-input__input" id="own-answer" name="own" rows="3" aria-describedby="own-answer-hint" bind:value={own} autofocus></textarea>
			</div>
		{/if}

		{#if failure}<p class="kern-error" role="alert"><span class="kern-icon kern-icon--danger" aria-hidden="true"></span><span class="kern-body">{failure}</span></p>{/if}

		<div class="kern-flex kern-flex-wrap kern-gap-md">
			<button type="submit" class="kern-btn kern-btn--primary" disabled={sending}>
				<span class="kern-label">{sending ? t('question.sending') : t('question.send')}</span>
				<span class="kern-icon kern-icon--arrow-forward" aria-hidden="true"></span>
			</button>
			<button type="button" class="kern-btn kern-btn--secondary" disabled={sending} onclick={() => send(true)}>
				<span class="kern-icon kern-icon--checklist" aria-hidden="true"></span>
				<span class="kern-label">{t('question.enough')}</span>
			</button>
		</div>
	</form>
</section>
