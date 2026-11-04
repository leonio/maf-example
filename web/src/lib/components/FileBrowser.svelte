<script lang="ts">
	// The generated app as it is on disk right now: a file list and the chosen file's content.
	import { api } from '#lib/api.ts';
	import { i18n } from '#lib/i18n.svelte.ts';

	let { runId, files }: { runId: string; files: string[] } = $props();
	const { t } = i18n;

	let selected = $state<string | null>(null);
	let content = $state<{ content: string; html: string | null } | null>(null);
	let failure = $state<string | null>(null);

	async function open(path: string) {
		failure = null;
		try {
			content = await api.file(runId, path);
		} catch (e) {
			content = null;
			failure = t('error.generic', { message: (e as Error).message });
		}
	}

	// Load the chosen file, and re-read it whenever the file list is refreshed (the agents may have rewritten it).
	$effect(() => {
		if (selected && files.includes(selected)) void open(selected);
	});
</script>

{#if files.length === 0}
	<p class="kern-body kern-body--muted">{t('files.empty')}</p>
{:else}
	<div class="kern-grid kern-grid-cols-1 kern-grid-cols-12-md kern-gap-lg">
		<nav class="kern-col-4-md" aria-label={t('files.title')}>
			<ul class="dp-files">
				{#each files as file (file)}
					<li>
						<button type="button" class="dp-files__item" aria-current={selected === file ? 'true' : undefined} onclick={() => (selected = file)}>
							<span class="kern-icon kern-icon--draft kern-icon--small" aria-hidden="true"></span>
							<code>{file}</code>
						</button>
					</li>
				{/each}
			</ul>
		</nav>
		<div class="kern-col-8-md dp-file-view">
			{#if failure}
				<p class="kern-error" role="alert"><span class="kern-icon kern-icon--danger" aria-hidden="true"></span><span class="kern-body">{failure}</span></p>
			{:else if content && content.html}
				<div class="dp-sheet dp-markdown">{@html content.html}</div>
			{:else if content}
				<pre class="dp-code" aria-label={selected ?? ''}><code>{content.content}</code></pre>
			{:else}
				<p class="kern-body kern-body--muted">{t('files.choose')}</p>
			{/if}
		</div>
	</div>
{/if}
