<script lang="ts">
	// The page frame: skip link, a one-row header (brand, main navigation as tabs, a segmented language switch; brand
	// and language on top, navigation below on small screens), <main>, and a footer. KERN's header pattern
	// (render_page) gives the structure; the look is ours, on KERN's tokens.
	import '@kern-ux/native/dist/fonts/fira-sans.css';
	import '@kern-ux/native/dist/kern.min.css';
	import '../app.css';

	import favicon from '#lib/assets/favicon.svg';
	import { api, type ServerConfig } from '#lib/api.ts';
	import { i18n, type Locale } from '#lib/i18n.svelte.ts';
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import type { LayoutProps } from './$types';

	let { children }: LayoutProps = $props();
	const { t } = i18n;

	let config = $state<ServerConfig | null>(null);
	onMount(async () => {
		try {
			config = await api.config();
		} catch {
			// the footer just leaves the model out
		}
	});

	$effect(() => {
		document.documentElement.lang = i18n.locale;
	});

	const links = $derived([
		{ href: '/', label: t('nav.new'), icon: 'add', current: page.url.pathname === '/' },
		{ href: '/runs', label: t('nav.runs'), icon: 'checklist', current: page.url.pathname.startsWith('/runs') }
	]);
	const locales: Locale[] = ['en', 'de'];
</script>

<svelte:head>
	<link rel="icon" href={favicon} />
</svelte:head>

<a class="kern-link kern-link--small dp-skip" href="#main">{t('nav.skip')}</a>

<header class="dp-header">
	<div class="kern-container dp-container dp-header__bar">
		<a class="dp-brand" href="/">
			<span class="dp-brand__mark" aria-hidden="true">DP</span>
			<span class="dp-brand__text">
				<span class="dp-brand__name">{t('app.name')}</span>
				<span class="dp-brand__tagline">{t('app.tagline')}</span>
			</span>
		</a>

		<nav class="dp-nav" aria-label={t('nav.main')}>
			<ul>
				{#each links as link (link.href)}
					<li>
						<a href={link.href} aria-current={link.current ? 'page' : undefined}>
							<span class="kern-icon kern-icon--{link.icon} kern-icon--small" aria-hidden="true"></span>
							{link.label}
						</a>
					</li>
				{/each}
			</ul>
		</nav>

		<div class="dp-lang" role="group" aria-label={t('nav.language')}>
			<span class="kern-icon kern-icon--language kern-icon--small" aria-hidden="true"></span>
			<span class="dp-lang__options">
				{#each locales as locale (locale)}
					<button type="button" lang={locale} aria-pressed={i18n.locale === locale} onclick={() => i18n.set(locale)}>
						<span aria-hidden="true">{locale.toUpperCase()}</span>
						<span class="kern-sr-only">{t(`lang.${locale}`)}</span>
					</button>
				{/each}
			</span>
		</div>
	</div>
</header>

<main id="main" class="kern-container dp-container">
	{@render children()}
</main>

<footer class="dp-footer">
	<div class="kern-container dp-container">
		<div class="kern-grid kern-grid-cols-1 kern-grid-cols-12-md kern-gap-lg">
			<div class="kern-col-8-md kern-stack-xs">
				<h2 class="kern-heading-small">{t('footer.about')}</h2>
				<p class="kern-body kern-body--small">{t('footer.text')}</p>
			</div>
			<div class="kern-col-4-md kern-stack-xs">
				<h2 class="kern-heading-small">{t('footer.provider')}</h2>
				<p class="kern-body kern-body--small">
					{#if config}{config.provider === 'mock' ? t('footer.mock') : `${config.provider} · ${config.model}`}{:else}…{/if}
				</p>
			</div>
		</div>
	</div>
</footer>
