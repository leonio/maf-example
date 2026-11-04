// English and German, switchable at any time. The choice is remembered per browser; the first visit follows the
// browser's language. The UI's language is the viewer's; the language the *agents* write in is chosen per run on the
// start form (it defaults to the UI language), so a German product owner and an English reviewer can watch the
// same run.

export type Locale = 'en' | 'de';

const en = {
	'app.name': 'Design pipeline',
	'app.tagline': 'From a one-line idea to a reviewed, ready-to-push app',
	'nav.new': 'New run',
	'nav.runs': 'Runs',
	'nav.language': 'Language',
	'nav.main': 'Main navigation',
	'nav.skip': 'Skip to content',
	'footer.about': 'About',
	'footer.text':
		'Four agents and two human gates on Microsoft Agent Framework for Python, with a SvelteKit UI built on KERN UX.',
	'footer.provider': 'Model',
	'footer.mock': 'Offline: scripted model',

	'home.title': 'What would you like to build?',
	'home.lead':
		'Describe a small app in a sentence or two. An interviewer agent asks you the questions everyone else forgets, you approve the spec, then a developer and a tester build and review it until it is good enough to ship, and a release agent prepares the merge request.',
	'home.idea': 'Your idea',
	'home.idea.hint': 'One or two sentences, e.g. “A tiny task tracker for my team”.',
	'home.idea.error': 'Describe the idea in at least a few words.',
	'home.settings': 'Run settings',
	'home.workItem': 'Work item',
	'home.workItem.hint': 'Jira key the work is filed under; used for the branch name and the tracker updates.',
	'home.workItem.error': 'Letters, digits, dashes and underscores only.',
	'home.maxQuestions': 'Interview questions',
	'home.maxQuestions.hint': 'At most this many questions before the spec is written ({min} to {max}).',
	'home.maxRounds': 'Review rounds',
	'home.maxRounds.hint':
		'Developer and tester rounds before it ships with whatever findings remain ({min} to {max}).',
	'home.number.error': 'Enter a whole number from {min} to {max}.',
	'home.agentLanguage': 'Language of the agents',
	'home.agentLanguage.hint': 'Questions, spec, reviews and the merge request are written in this language.',
	'home.auto': 'Answer automatically (first suggestion, then approve)',
	'home.auto.hint': 'Handy for a quick demo: you only watch.',
	'home.start': 'Start the run',
	'home.starting': 'Starting…',
	'home.how': 'How it works',
	'home.mockNote':
		'This server runs offline with a scripted model: whatever you type, it builds the same small task tracker, but the agents, tools and workflow all run for real. Set PIPELINE_PROVIDER to use a real model.',
	'home.recent': 'Recent runs',
	'home.allRuns': 'All runs',

	'stage.interview': 'Interview',
	'stage.interview.text': 'One question at a time, until the idea is buildable.',
	'stage.approval': 'Spec approval',
	'stage.approval.text': 'Nothing is built until you approve the spec.',
	'stage.develop': 'Development',
	'stage.develop.text': 'The developer writes the app through sandboxed file tools.',
	'stage.test': 'Review and tests',
	'stage.test.text': 'The tester checks every acceptance criterion and writes tests.',
	'stage.release': 'Merge request',
	'stage.release.text': 'Pull request, Jira and Confluence, and the git commands.',

	'status.open': 'Open',
	'status.active': 'In progress',
	'status.waiting': 'Waiting for you',
	'status.done': 'Done',
	'status.failed': 'Failed',
	'run.status.running': 'Running',
	'run.status.waiting': 'Waiting for you',
	'run.status.done': 'Done',
	'run.status.failed': 'Failed',
	'run.status.cancelled': 'Cancelled',
	'run.status.interrupted': 'Interrupted',

	'runs.title': 'Runs',
	'runs.lead': 'Every run keeps its spec, reviews, decisions and generated app in its own folder under output/.',
	'runs.caption': 'All runs, newest first',
	'runs.empty': 'No runs yet.',
	'runs.idea': 'Idea',
	'runs.started': 'Started',
	'runs.status': 'Status',
	'runs.rounds': 'Rounds',
	'runs.verdict': 'Verdict',

	'run.stages': 'Stages',
	'run.stagesDone': '{done} of {total} done',
	'run.facts': 'This run',
	'run.workItem': 'Work item',
	'run.started': 'Started',
	'run.language': 'Agents write in',
	'run.budget': 'Question budget',
	'run.rounds': 'Review rounds',
	'run.answering': 'Answers',
	'run.answering.auto': 'Automatic',
	'run.answering.you': 'You',
	'run.download': 'Download app and documents (.zip)',
	'run.cancel': 'Cancel run',
	'run.cancelConfirm': 'Cancel this run? It cannot be resumed.',
	'run.loading': 'Loading the run…',
	'run.notFound': 'There is no run with this id.',
	'run.working': 'The agents are working…',
	'run.failed': 'The run failed',
	'run.cancelled': 'The run was cancelled',
	'run.interrupted': 'The run was interrupted',
	'run.interrupted.text':
		'The server stopped while this run was in progress. Runs live in memory while they work; start a new run to try again.',
	'run.connection': 'Lost the connection to the server, reconnecting…',

	'question.title': 'Question {n} of {budget}',
	'question.why': 'Why this matters',
	'question.suggestions': 'Suggested answers',
	'question.own': 'Your own answer',
	'question.own.option': 'Something else',
	'question.own.hint': 'Free text. It goes to the interviewer as it is.',
	'question.error': 'Pick a suggestion or write your own answer.',
	'question.send': 'Send answer',
	'question.enough': 'That’s enough, write the spec',
	'question.sending': 'Sending…',

	'approval.title': 'Approve the specification?',
	'approval.lead': 'Nothing is built until you approve this. Your reason is kept next to the spec in decisions.jsonl.',
	'approval.decision': 'Your decision',
	'approval.approve': 'Approve, start building',
	'approval.reject': 'Reject, send it back',
	'approval.reason': 'Reason',
	'approval.reason.approveHint': 'Optional: why it is good to go.',
	'approval.reason.rejectHint': 'Required: what is wrong or missing. The interviewer revises the spec with it.',
	'approval.reason.error': 'Say what is wrong or missing, so the interviewer can fix it.',
	'approval.submit': 'Send decision',

	'spec.primaryUser': 'Primary user',
	'spec.appKind': 'App kind',
	'spec.userStories': 'User stories',
	'spec.acceptance': 'Acceptance criteria',
	'spec.assumptions': 'Assumptions',
	'spec.outOfScope': 'Out of scope',
	'spec.none': 'None.',
	'spec.approved': 'Approved specification',

	'result.title': 'Ready for review',
	'result.lead': 'The merge request is prepared. The pull request step is mocked unless MCP is switched on.',
	'result.branch': 'Branch',
	'result.pr': 'Pull request',
	'result.prNone': 'Not created',
	'result.commands': 'Push it yourself',
	'result.copy': 'Copy commands',
	'result.copied': 'Copied',
	'result.notes': 'Notes',

	'reviews.title': 'Reviews',
	'reviews.round': 'Round {n}',
	'reviews.next': 'Next step',
	'reviews.findings': 'Findings',
	'reviews.noFindings': 'No findings.',
	'reviews.severity': 'Severity',
	'reviews.file': 'File',
	'reviews.finding': 'Finding',
	'reviews.tests': 'Tests written',
	'verdict.Approved': 'Approved',
	'verdict.ChangesRequested': 'Changes requested',
	'next.Rework': 'Rework',
	'next.Ship': 'Ship',
	'severity.High': 'High',
	'severity.Medium': 'Medium',
	'severity.Low': 'Low',

	'interview.title': 'Interview',
	'interview.empty': 'No questions yet.',
	'interview.you': 'You',
	'interview.auto': 'automatic',
	'interview.ended': 'Ended the interview',
	'interview.approved': 'Approved the spec',
	'interview.rejected': 'Rejected the spec',

	'activity.title': 'Activity',
	'activity.tools': 'Show tool calls',
	'activity.count': '{n} events',

	'files.title': 'Generated app',
	'files.empty': 'No files yet.',
	'files.choose': 'Choose a file to look at it.',
	'files.run': 'Run its tests',

	'workflow.title': 'Workflow graph',
	'workflow.lead': 'Generated from the workflow definition when the run started (workflow.mmd).',

	'event.started': 'Run started ({provider})',
	'event.question': 'Question {n}: {question}',
	'event.approval': 'Specification ready for approval',
	'event.answered': 'Answered',
	'event.review': 'Review round {n}: {verdict}',
	'event.result': 'Merge request ready',
	'event.status.running': 'Running again',
	'event.status.waiting': 'Waiting for your answer',
	'event.status.done': 'Finished',
	'event.status.failed': 'Failed: {error}',
	'event.status.cancelled': 'Cancelled',

	'code.interview.started': 'Interview started for “{idea}”',
	'code.interview.approved': 'Spec approved and saved to SPEC.md',
	'code.interview.rejected': 'Spec rejected; back to the interviewer',
	'code.develop.started.first': 'Implementing the spec…',
	'code.develop.started': 'Rework round {round}: fixing the review findings…',
	'code.develop.done': 'Round {round} written ({files} files in the workspace)',
	'code.test.started': 'Reviewing round {round} ({files} files)…',
	'code.test.done': 'Round {round}: {verdict}, {findings} finding(s), next: {next}',
	'code.release.started': 'Preparing the merge request and updating Jira and Confluence…',
	'code.release.done': 'Merge request notes saved to MERGE_REQUEST.md',

	'lang.en': 'English',
	'lang.de': 'Deutsch',
	'form.optional': 'optional',
	'form.errors': 'Please check your entries',
	'error.generic': 'Something went wrong: {message}'
};

type Key = keyof typeof en;

const de: Record<Key, string> = {
	'app.name': 'Design-Pipeline',
	'app.tagline': 'Von der Idee in einem Satz zur geprüften, push-fertigen App',
	'nav.new': 'Neuer Lauf',
	'nav.runs': 'Läufe',
	'nav.language': 'Sprache',
	'nav.main': 'Hauptnavigation',
	'nav.skip': 'Zum Inhalt springen',
	'footer.about': 'Über',
	'footer.text':
		'Vier Agenten und zwei menschliche Freigaben auf Microsoft Agent Framework für Python, mit einer SvelteKit-Oberfläche auf Basis von KERN UX.',
	'footer.provider': 'Modell',
	'footer.mock': 'Offline: skriptgesteuertes Modell',

	'home.title': 'Was möchten Sie bauen?',
	'home.lead':
		'Beschreiben Sie eine kleine App in ein, zwei Sätzen. Ein Interview-Agent stellt Ihnen die Fragen, die sonst alle vergessen, Sie geben die Spezifikation frei, dann bauen und prüfen ein Entwickler und ein Tester die App, bis sie gut genug ist, und ein Release-Agent bereitet den Merge Request vor.',
	'home.idea': 'Ihre Idee',
	'home.idea.hint': 'Ein, zwei Sätze, z. B. „Eine kleine Aufgabenliste für mein Team“.',
	'home.idea.error': 'Beschreiben Sie die Idee in wenigstens ein paar Worten.',
	'home.settings': 'Einstellungen für den Lauf',
	'home.workItem': 'Vorgang',
	'home.workItem.hint': 'Jira-Schlüssel, unter dem die Arbeit läuft; für den Branch-Namen und die Ticket-Updates.',
	'home.workItem.error': 'Nur Buchstaben, Ziffern, Bindestriche und Unterstriche.',
	'home.maxQuestions': 'Interviewfragen',
	'home.maxQuestions.hint': 'Höchstens so viele Fragen, bevor die Spezifikation geschrieben wird ({min} bis {max}).',
	'home.maxRounds': 'Review-Runden',
	'home.maxRounds.hint':
		'Runden aus Entwicklung und Test, bevor mit den offenen Befunden ausgeliefert wird ({min} bis {max}).',
	'home.number.error': 'Geben Sie eine ganze Zahl von {min} bis {max} ein.',
	'home.agentLanguage': 'Sprache der Agenten',
	'home.agentLanguage.hint': 'Fragen, Spezifikation, Reviews und Merge Request werden in dieser Sprache geschrieben.',
	'home.auto': 'Automatisch antworten (erster Vorschlag, dann freigeben)',
	'home.auto.hint': 'Praktisch für eine schnelle Vorführung: Sie schauen nur zu.',
	'home.start': 'Lauf starten',
	'home.starting': 'Wird gestartet …',
	'home.how': 'So funktioniert es',
	'home.mockNote':
		'Dieser Server läuft offline mit einem skriptgesteuerten Modell: Was Sie auch eingeben, er baut dieselbe kleine Aufgabenliste, aber Agenten, Werkzeuge und Workflow laufen echt. Mit PIPELINE_PROVIDER nutzen Sie ein echtes Modell.',
	'home.recent': 'Letzte Läufe',
	'home.allRuns': 'Alle Läufe',

	'stage.interview': 'Interview',
	'stage.interview.text': 'Eine Frage nach der anderen, bis die Idee baubar ist.',
	'stage.approval': 'Freigabe der Spezifikation',
	'stage.approval.text': 'Gebaut wird erst, wenn Sie die Spezifikation freigeben.',
	'stage.develop': 'Entwicklung',
	'stage.develop.text': 'Der Entwickler schreibt die App über abgeschottete Datei-Werkzeuge.',
	'stage.test': 'Review und Tests',
	'stage.test.text': 'Der Tester prüft jedes Akzeptanzkriterium und schreibt Tests.',
	'stage.release': 'Merge Request',
	'stage.release.text': 'Pull Request, Jira und Confluence, und die Git-Befehle.',

	'status.open': 'Offen',
	'status.active': 'In Arbeit',
	'status.waiting': 'Wartet auf Sie',
	'status.done': 'Erledigt',
	'status.failed': 'Fehlgeschlagen',
	'run.status.running': 'Läuft',
	'run.status.waiting': 'Wartet auf Sie',
	'run.status.done': 'Fertig',
	'run.status.failed': 'Fehlgeschlagen',
	'run.status.cancelled': 'Abgebrochen',
	'run.status.interrupted': 'Unterbrochen',

	'runs.title': 'Läufe',
	'runs.lead':
		'Jeder Lauf bewahrt Spezifikation, Reviews, Entscheidungen und die erzeugte App in einem eigenen Ordner unter output/ auf.',
	'runs.caption': 'Alle Läufe, die neuesten zuerst',
	'runs.empty': 'Noch keine Läufe.',
	'runs.idea': 'Idee',
	'runs.started': 'Gestartet',
	'runs.status': 'Status',
	'runs.rounds': 'Runden',
	'runs.verdict': 'Ergebnis',

	'run.stages': 'Schritte',
	'run.stagesDone': '{done} von {total} erledigt',
	'run.facts': 'Dieser Lauf',
	'run.workItem': 'Vorgang',
	'run.started': 'Gestartet',
	'run.language': 'Agenten schreiben auf',
	'run.budget': 'Fragenbudget',
	'run.rounds': 'Review-Runden',
	'run.answering': 'Antworten',
	'run.answering.auto': 'Automatisch',
	'run.answering.you': 'Sie',
	'run.download': 'App und Dokumente herunterladen (.zip)',
	'run.cancel': 'Lauf abbrechen',
	'run.cancelConfirm': 'Diesen Lauf abbrechen? Er kann nicht fortgesetzt werden.',
	'run.loading': 'Der Lauf wird geladen …',
	'run.notFound': 'Es gibt keinen Lauf mit dieser Kennung.',
	'run.working': 'Die Agenten arbeiten …',
	'run.failed': 'Der Lauf ist fehlgeschlagen',
	'run.cancelled': 'Der Lauf wurde abgebrochen',
	'run.interrupted': 'Der Lauf wurde unterbrochen',
	'run.interrupted.text':
		'Der Server wurde angehalten, während dieser Lauf arbeitete. Läufe leben während der Arbeit im Speicher; starten Sie einen neuen Lauf.',
	'run.connection': 'Verbindung zum Server verloren, verbinde neu …',

	'question.title': 'Frage {n} von {budget}',
	'question.why': 'Warum das wichtig ist',
	'question.suggestions': 'Vorgeschlagene Antworten',
	'question.own': 'Ihre eigene Antwort',
	'question.own.option': 'Etwas anderes',
	'question.own.hint': 'Freitext. Er geht so, wie er ist, an den Interviewer.',
	'question.error': 'Wählen Sie einen Vorschlag oder schreiben Sie eine eigene Antwort.',
	'question.send': 'Antwort senden',
	'question.enough': 'Genug gefragt, Spezifikation schreiben',
	'question.sending': 'Wird gesendet …',

	'approval.title': 'Spezifikation freigeben?',
	'approval.lead':
		'Gebaut wird erst nach Ihrer Freigabe. Ihre Begründung wird neben der Spezifikation in decisions.jsonl aufbewahrt.',
	'approval.decision': 'Ihre Entscheidung',
	'approval.approve': 'Freigeben, mit dem Bauen beginnen',
	'approval.reject': 'Ablehnen, zurückschicken',
	'approval.reason': 'Begründung',
	'approval.reason.approveHint': 'Optional: warum es so passt.',
	'approval.reason.rejectHint':
		'Pflicht: was falsch ist oder fehlt. Der Interviewer überarbeitet die Spezifikation damit.',
	'approval.reason.error': 'Sagen Sie, was falsch ist oder fehlt, damit der Interviewer es beheben kann.',
	'approval.submit': 'Entscheidung senden',

	'spec.primaryUser': 'Hauptnutzer',
	'spec.appKind': 'Art der App',
	'spec.userStories': 'User Stories',
	'spec.acceptance': 'Akzeptanzkriterien',
	'spec.assumptions': 'Annahmen',
	'spec.outOfScope': 'Nicht im Umfang',
	'spec.none': 'Keine.',
	'spec.approved': 'Freigegebene Spezifikation',

	'result.title': 'Bereit zum Review',
	'result.lead':
		'Der Merge Request ist vorbereitet. Der Pull-Request-Schritt ist simuliert, solange MCP nicht eingeschaltet ist.',
	'result.branch': 'Branch',
	'result.pr': 'Pull Request',
	'result.prNone': 'Nicht angelegt',
	'result.commands': 'Selbst pushen',
	'result.copy': 'Befehle kopieren',
	'result.copied': 'Kopiert',
	'result.notes': 'Hinweise',

	'reviews.title': 'Reviews',
	'reviews.round': 'Runde {n}',
	'reviews.next': 'Nächster Schritt',
	'reviews.findings': 'Befunde',
	'reviews.noFindings': 'Keine Befunde.',
	'reviews.severity': 'Schwere',
	'reviews.file': 'Datei',
	'reviews.finding': 'Befund',
	'reviews.tests': 'Geschriebene Tests',
	'verdict.Approved': 'Freigegeben',
	'verdict.ChangesRequested': 'Änderungen nötig',
	'next.Rework': 'Nacharbeit',
	'next.Ship': 'Ausliefern',
	'severity.High': 'Hoch',
	'severity.Medium': 'Mittel',
	'severity.Low': 'Niedrig',

	'interview.title': 'Interview',
	'interview.empty': 'Noch keine Fragen.',
	'interview.you': 'Sie',
	'interview.auto': 'automatisch',
	'interview.ended': 'Interview beendet',
	'interview.approved': 'Spezifikation freigegeben',
	'interview.rejected': 'Spezifikation abgelehnt',

	'activity.title': 'Verlauf',
	'activity.tools': 'Werkzeugaufrufe anzeigen',
	'activity.count': '{n} Ereignisse',

	'files.title': 'Erzeugte App',
	'files.empty': 'Noch keine Dateien.',
	'files.choose': 'Wählen Sie eine Datei, um sie anzusehen.',
	'files.run': 'Tests ausführen',

	'workflow.title': 'Workflow-Graph',
	'workflow.lead': 'Beim Start des Laufs aus der Workflow-Definition erzeugt (workflow.mmd).',

	'event.started': 'Lauf gestartet ({provider})',
	'event.question': 'Frage {n}: {question}',
	'event.approval': 'Spezifikation bereit zur Freigabe',
	'event.answered': 'Beantwortet',
	'event.review': 'Review-Runde {n}: {verdict}',
	'event.result': 'Merge Request bereit',
	'event.status.running': 'Läuft weiter',
	'event.status.waiting': 'Wartet auf Ihre Antwort',
	'event.status.done': 'Fertig',
	'event.status.failed': 'Fehlgeschlagen: {error}',
	'event.status.cancelled': 'Abgebrochen',

	'code.interview.started': 'Interview gestartet für „{idea}“',
	'code.interview.approved': 'Spezifikation freigegeben und in SPEC.md gespeichert',
	'code.interview.rejected': 'Spezifikation abgelehnt; zurück zum Interviewer',
	'code.develop.started.first': 'Die Spezifikation wird umgesetzt …',
	'code.develop.started': 'Nacharbeit, Runde {round}: die Review-Befunde werden behoben …',
	'code.develop.done': 'Runde {round} geschrieben ({files} Dateien im Arbeitsbereich)',
	'code.test.started': 'Runde {round} wird geprüft ({files} Dateien) …',
	'code.test.done': 'Runde {round}: {verdict}, {findings} Befund(e), weiter mit: {next}',
	'code.release.started': 'Merge Request wird vorbereitet, Jira und Confluence werden aktualisiert …',
	'code.release.done': 'Merge-Request-Notizen in MERGE_REQUEST.md gespeichert',

	'lang.en': 'English',
	'lang.de': 'Deutsch',
	'form.optional': 'optional',
	'form.errors': 'Bitte prüfen Sie Ihre Angaben',
	'error.generic': 'Etwas ist schiefgegangen: {message}'
};

const dictionaries: Record<Locale, Record<Key, string>> = { en, de };
const STORAGE_KEY = 'design-pipeline.locale';

function initial(): Locale {
	try {
		const saved = localStorage.getItem(STORAGE_KEY);
		if (saved === 'en' || saved === 'de') return saved;
	} catch {
		// private mode or blocked storage: fall through to the browser language
	}
	return navigator.language?.toLowerCase().startsWith('de') ? 'de' : 'en';
}

class I18n {
	locale = $state<Locale>(initial());

	set(locale: Locale) {
		this.locale = locale;
		try {
			localStorage.setItem(STORAGE_KEY, locale);
		} catch {
			// not remembered, still switched
		}
	}

	t = (key: Key, params: Record<string, unknown> = {}): string => {
		const template = dictionaries[this.locale][key] ?? en[key] ?? key;
		return template.replace(/\{(\w+)\}/g, (_, name) => String(params[name] ?? `{${name}}`));
	};

	/** Translate a key built at runtime (stage codes, verdicts); falls back to the raw text. */
	tx = (key: string, params: Record<string, unknown> = {}, fallback?: string): string =>
		key in en ? this.t(key as Key, params) : (fallback ?? key);

	date = (iso: string): string =>
		new Date(iso).toLocaleString(this.locale === 'de' ? 'de-DE' : 'en-GB', {
			dateStyle: 'medium',
			timeStyle: 'short'
		});

	time = (iso: string): string =>
		new Date(iso).toLocaleTimeString(this.locale === 'de' ? 'de-DE' : 'en-GB', {
			hour: '2-digit',
			minute: '2-digit',
			second: '2-digit'
		});
}

export const i18n = new I18n();
export type { Key };
