<script lang="ts">
	// The human gate before any code is written. The decision is a KERN radio group (approve / reject), the reason a
	// KERN textarea that becomes required on reject; the error follows KERN's pattern (message above the field,
	// linked with aria-describedby).
	import { api, type Spec } from '#lib/api.ts';
	import { i18n } from '#lib/i18n.svelte.ts';
	import SpecView from './SpecView.svelte';

	let { runId, requestId, spec }: { runId: string; requestId: string; spec: Spec } = $props();
	const { t } = i18n;

	let decision = $state<'approve' | 'reject'>('approve');
	let reason = $state('');
	let error = $state<string | null>(null);
	let failure = $state<string | null>(null);
	let sending = $state(false);

	async function submit(e: SubmitEvent) {
		e.preventDefault();
		failure = null;
		if (decision === 'reject' && !reason.trim()) {
			error = t('approval.reason.error');
			document.getElementById('reason')?.focus();
			return;
		}
		error = null;
		sending = true;
		try {
			await api.decide(runId, requestId, decision === 'approve', reason.trim());
		} catch (err) {
			failure = t('error.generic', { message: (err as Error).message });
			sending = false;
		}
	}
</script>

<section class="dp-panel dp-panel--action kern-stack-lg" aria-labelledby="approval-title">
	<div class="kern-stack-xs">
		<p class="kern-preline">{t('stage.approval')}</p>
		<h2 class="kern-heading-medium" id="approval-title">{t('approval.title')}</h2>
		<p class="kern-body kern-body--muted">{t('approval.lead')}</p>
	</div>

	<div class="dp-sheet"><SpecView {spec} /></div>

	<form class="kern-stack-lg" novalidate onsubmit={submit}>
		<fieldset class="kern-fieldset">
			<legend class="kern-label">{t('approval.decision')}</legend>
			<div class="kern-fieldset__body">
				<div class="kern-form-check">
					<input class="kern-form-check__radio" id="decision-approve" name="decision" type="radio" value="approve" bind:group={decision} />
					<label class="kern-label" for="decision-approve">{t('approval.approve')}</label>
				</div>
				<div class="kern-form-check">
					<input class="kern-form-check__radio" id="decision-reject" name="decision" type="radio" value="reject" bind:group={decision} />
					<label class="kern-label" for="decision-reject">{t('approval.reject')}</label>
				</div>
			</div>
		</fieldset>

		<div class="kern-form-input" class:kern-form-input--error={error}>
			<label class="kern-label" for="reason">
				{t('approval.reason')}
				{#if decision === 'approve'}<span class="kern-label__optional">({t('form.optional')})</span>{/if}
			</label>
			<div class="kern-hint" id="reason-hint">
				{decision === 'approve' ? t('approval.reason.approveHint') : t('approval.reason.rejectHint')}
			</div>
			{#if error}
				<p class="kern-error" id="reason-error" role="alert">
					<span class="kern-icon kern-icon--danger" aria-hidden="true"></span>
					<span class="kern-body">{error}</span>
				</p>
			{/if}
			<textarea
				class="kern-form-input__input"
				class:kern-form-input__input--error={error}
				id="reason"
				name="reason"
				rows="3"
				required={decision === 'reject'}
				aria-required={decision === 'reject'}
				aria-invalid={error ? true : undefined}
				aria-describedby={error ? 'reason-hint reason-error' : 'reason-hint'}
				bind:value={reason}
			></textarea>
		</div>

		{#if failure}<p class="kern-error" role="alert"><span class="kern-icon kern-icon--danger" aria-hidden="true"></span><span class="kern-body">{failure}</span></p>{/if}

		<div>
			<button type="submit" class="kern-btn kern-btn--primary" disabled={sending}>
				<span class="kern-icon kern-icon--{decision === 'approve' ? 'check' : 'arrow-back'}" aria-hidden="true"></span>
				<span class="kern-label">{sending ? t('question.sending') : decision === 'approve' ? t('approval.approve') : t('approval.reject')}</span>
			</button>
		</div>
	</form>
</section>
