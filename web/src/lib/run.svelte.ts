// One run as the page sees it: the snapshot from GET /api/runs/{id}, then every live event from the server-sent
// stream folded in. All view state (stages, interview transcript, reviews, result) is derived from the events, so a
// reload, a second tab and a reconnect all end up showing the same thing.

import { api, type Pending, type RunDetail, type RunEvent, type RunStatus } from './api';

export const STAGES = ['interview', 'approval', 'develop', 'test', 'release'] as const;
export type Stage = (typeof STAGES)[number];
export type StageState = 'open' | 'active' | 'waiting' | 'done' | 'failed';

const STAGE_OF: Record<string, Stage> = {
	interview: 'interview',
	develop: 'develop',
	test: 'test',
	release: 'release'
};

export class LiveRun {
	detail = $state<RunDetail | null>(null);
	events = $state<RunEvent[]>([]);
	files = $state<string[]>([]);
	notFound = $state(false);
	connected = $state(true);
	error = $state<string | null>(null);

	#source: EventSource | null = null;
	#id: string;

	constructor(id: string) {
		this.#id = id;
	}

	get status(): RunStatus | undefined {
		const last = this.events.findLast((e) => e.kind === 'status');
		return (last?.kind === 'status' ? last.status : undefined) ?? this.detail?.status;
	}

	get isActive() {
		return this.status === 'running' || this.status === 'waiting';
	}

	/** The open request, if the latest question/approval has not been answered yet. */
	get pending(): Pending | null {
		const answered = new Set(this.events.filter((e) => e.kind === 'answered').map((e) => e.requestId));
		const open = this.events.findLast(
			(e) => (e.kind === 'question' || e.kind === 'approval') && !answered.has(e.requestId)
		);
		if (!open || !this.isActive) return null;
		return open.kind === 'question'
			? { requestId: open.requestId, kind: 'question', question: open.question }
			: open.kind === 'approval'
				? { requestId: open.requestId, kind: 'approval', spec: open.spec }
				: null;
	}

	get reviews() {
		return this.events.flatMap((e) => (e.kind === 'review' ? [e.review] : []));
	}

	get result() {
		const e = this.events.findLast((e) => e.kind === 'result');
		return e?.kind === 'result' ? e.plan : null;
	}

	get approvedSpec() {
		const approvals = new Map(
			this.events.flatMap((e) => (e.kind === 'approval' ? [[e.requestId, e.spec] as const] : []))
		);
		const yes = this.events.findLast((e) => e.kind === 'answered' && e.response.approved === true);
		return yes?.kind === 'answered' ? (approvals.get(yes.requestId) ?? null) : null;
	}

	/** Question/approval and answer pairs, in order. */
	get transcript() {
		const answers = new Map(this.events.flatMap((e) => (e.kind === 'answered' ? [[e.requestId, e] as const] : [])));
		return this.events.flatMap((e) =>
			e.kind === 'question' || e.kind === 'approval' ? [{ ask: e, answer: answers.get(e.requestId) }] : []
		);
	}

	/** Why the run failed, if it did. */
	get failure() {
		const e = this.events.findLast((e) => e.kind === 'status' && e.status === 'failed');
		return e?.kind === 'status' ? e.error : (this.detail?.error ?? null);
	}

	get stages(): Record<Stage, StageState> {
		const state = Object.fromEntries(STAGES.map((s) => [s, 'open'])) as Record<Stage, StageState>;
		const status = this.status;
		if (status === 'done') {
			for (const s of STAGES) state[s] = 'done';
			return state;
		}
		// The current stage is the one the latest stage-ish event belongs to.
		let current: Stage = 'interview';
		for (const e of this.events) {
			if (e.kind === 'stage') {
				current = e.code === 'interview.approved' ? 'develop' : (STAGE_OF[e.stage] ?? current);
			} else if (e.kind === 'question') current = 'interview';
			else if (e.kind === 'approval') current = 'approval';
		}
		const index = STAGES.indexOf(current);
		STAGES.forEach((s, i) => {
			if (i < index) state[s] = 'done';
		});
		const pending = this.pending;
		state[current] =
			status === 'failed' || status === 'cancelled' || status === 'interrupted'
				? 'failed'
				: pending
					? 'waiting'
					: 'active';
		return state;
	}

	async load() {
		try {
			const detail = await api.run(this.#id);
			this.detail = detail;
			this.events = detail.events;
			this.files = detail.files;
			if (detail.status === 'running' || detail.status === 'waiting') this.#follow();
		} catch (e) {
			if ((e as { status?: number }).status === 404) this.notFound = true;
			else this.error = (e as Error).message;
		}
	}

	#follow() {
		const after = this.events.at(-1)?.seq ?? 0;
		// EventSource reconnects by itself and sends Last-Event-ID, so the server resumes from the right place.
		const source = new EventSource(api.streamUrl(this.#id, after));
		this.#source = source;
		source.onopen = () => (this.connected = true);
		source.onmessage = (message) => {
			const event = JSON.parse(message.data) as RunEvent;
			if (this.events.at(-1) && event.seq <= this.events.at(-1)!.seq) return;
			this.events.push(event);
			if (event.kind === 'tool' && /write_(test_)?file/.test(event.tool)) void this.refreshFiles();
			if (event.kind === 'status' && !['running', 'waiting'].includes(event.status)) void this.refreshFiles();
		};
		source.addEventListener('end', () => this.close());
		source.onerror = () => {
			this.connected = source.readyState === EventSource.OPEN;
		};
	}

	async refreshFiles() {
		try {
			this.files = (await api.run(this.#id)).files;
		} catch {
			// next event will try again
		}
	}

	close() {
		this.#source?.close();
		this.#source = null;
		this.connected = true;
	}
}
