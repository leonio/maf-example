// The Python API, typed. Shapes mirror designpipeline/contracts.py (camelCase on the wire).

export type RunStatus = 'running' | 'waiting' | 'done' | 'failed' | 'cancelled' | 'interrupted';
export type Verdict = 'Approved' | 'ChangesRequested';
export type Severity = 'Low' | 'Medium' | 'High';

export interface Spec {
	title: string;
	summary: string;
	primaryUser: string;
	appKind: string;
	userStories: string[];
	acceptanceCriteria: string[];
	assumptions: string[];
	outOfScope: string[];
}

export interface Question {
	number: number;
	budget: number;
	question: string;
	why: string;
	suggestedAnswers: string[];
}

export interface Finding {
	severity: Severity;
	file: string;
	message: string;
}

export interface ReviewOutcome {
	round: number;
	next: 'Rework' | 'Ship';
	report: { verdict: Verdict; summary: string; findings: Finding[]; testsWritten: string[] };
}

export interface MergeRequestPlan {
	branch: string;
	title: string;
	body: string;
	bodyHtml: string;
	commands: string[];
	pullRequestUrl: string | null;
	notes: string[];
}

export type Pending =
	| { requestId: string; kind: 'question'; question: Question }
	| { requestId: string; kind: 'approval'; spec: Spec };

interface Base {
	seq: number;
	at: string;
}

export type RunEvent = Base &
	(
		| { kind: 'started'; provider: string; model: string | null }
		| { kind: 'stage'; stage: string; code: string; params: Record<string, unknown>; detail: string | null }
		| { kind: 'tool'; agent: string; tool: string; arguments: string; result: string }
		| { kind: 'question'; requestId: string; question: Question }
		| { kind: 'approval'; requestId: string; spec: Spec }
		| {
				kind: 'answered';
				requestId: string;
				auto: boolean;
				response: { text?: string; endInterview?: boolean; approved?: boolean; reason?: string | null };
		  }
		| { kind: 'review'; review: ReviewOutcome }
		| { kind: 'result'; plan: MergeRequestPlan }
		| { kind: 'status'; status: RunStatus; error: string | null }
	);

export interface RunMeta {
	id: string;
	createdAt: string;
	status: RunStatus;
	error: string | null;
	title: string | null;
	verdict: Verdict | null;
	rounds: number;
	options: {
		idea: string;
		workItemKey: string;
		maxQuestions: number;
		maxReviewRounds: number;
		language: 'en' | 'de';
		autoAnswer: boolean;
	};
}

export interface RunDetail extends RunMeta {
	pending: Pending | null;
	events: RunEvent[];
	files: string[];
}

export interface ServerConfig {
	provider: string;
	model: string | null;
	defaults: { maxQuestions: number; maxReviewRounds: number; workItemKey: string };
	limits: { max_questions: [number, number]; max_review_rounds: [number, number] };
	integrations: { jira: string; confluence: string; github: string };
}

export class ApiError extends Error {
	constructor(
		public status: number,
		message: string
	) {
		super(message);
	}
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
	const response = await fetch(`/api${path}`, {
		...init,
		headers: { 'Content-Type': 'application/json', ...(init?.headers ?? {}) }
	});
	if (!response.ok) {
		let message = response.statusText;
		try {
			const body = await response.json();
			message =
				typeof body.detail === 'string'
					? body.detail
					: Array.isArray(body.detail)
						? body.detail.map((d: { msg: string }) => d.msg).join('; ')
						: message;
		} catch {
			// not JSON
		}
		throw new ApiError(response.status, message);
	}
	const type = response.headers.get('content-type') ?? '';
	return (type.includes('json') ? response.json() : response.text()) as Promise<T>;
}

const post = (body: unknown): RequestInit => ({ method: 'POST', body: JSON.stringify(body) });

export const api = {
	config: () => request<ServerConfig>('/config'),
	runs: () => request<RunMeta[]>('/runs'),
	run: (id: string) => request<RunDetail>(`/runs/${encodeURIComponent(id)}`),
	start: (body: {
		idea: string;
		workItemKey: string;
		maxQuestions: number;
		maxReviewRounds: number;
		language: 'en' | 'de';
		autoAnswer: boolean;
	}) => request<RunMeta>('/runs', post(body)),
	answer: (id: string, requestId: string, text: string, endInterview = false) =>
		request(`/runs/${encodeURIComponent(id)}/answer`, post({ requestId, text, endInterview })),
	decide: (id: string, requestId: string, approved: boolean, reason: string) =>
		request(`/runs/${encodeURIComponent(id)}/decision`, post({ requestId, approved, reason })),
	cancel: (id: string) => request(`/runs/${encodeURIComponent(id)}/cancel`, post({})),
	file: (id: string, path: string) =>
		request<{ path: string; content: string; html: string | null }>(
			`/runs/${encodeURIComponent(id)}/files/${path.split('/').map(encodeURIComponent).join('/')}`
		),
	artifact: (id: string, name: string) => request<string>(`/runs/${encodeURIComponent(id)}/artifacts/${name}`),
	streamUrl: (id: string, after: number) => `/api/runs/${encodeURIComponent(id)}/stream?after=${after}`,
	downloadUrl: (id: string) => `/api/runs/${encodeURIComponent(id)}/download`
};
