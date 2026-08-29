import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';

import { isApiError } from '../../api/client.ts';
import type { AiAnswer } from '../../api/client.ts';
import { postAiExplain, useAiStatus } from '../../api/decisionApi.ts';
import { pageStateOf } from '../../api/hooks.ts';
import { usePortfolio } from '../../api/portfolioApi.ts';
import { AuthRequiredNotice } from '../../components/AuthRequiredNotice.tsx';
import { DataStateBoundary } from '../../components/DataStateBoundary.tsx';
import type { DataState } from '../../components/DataStateBoundary.tsx';
import { DEV_SYNTHETIC_UNDERLYINGS } from '../devUniverse.ts';
import {
  AI_NOTE_CAPABILITY_STATE,
  AI_PERMANENT_NOTICE,
  AI_SUBJECT_KINDS,
  AI_SUBJECT_LABELS,
  AI_SUBJECT_RESOURCE_LABELS,
  isAiSubjectKind,
} from './aiView.ts';
import type { AiSubjectKind } from './aiView.ts';
import {
  ClaimsBlock,
  ContradictionsBlock,
  EvidenceCatalogBlock,
  ExternalExcerptsBlock,
  LimitationsBlock,
  MissingDataBlock,
  RefusalBlock,
  TraceabilityBlock,
} from './AiAnswerView.tsx';

/**
 * Page Vertex IA — question : « Comment expliquer, relier et résumer les
 * données certifiées sans créer une seconde vérité ? »
 *
 * Aucun fournisseur d'IA n'existe dans ce dépôt : la décision B-05 est en
 * attente et `/ai/status` le dit. Le seul chemin d'explication est le gabarit
 * DÉTERMINISTE du serveur, fonction pure d'UN snapshot persisté. La page
 * affiche la réponse telle quelle : refus explicite, affirmations avec
 * citations ouvrables, extraits externes isolés, contradictions, données
 * manquantes, limites et traçabilité complète.
 */

const ERROR_NO_SNAPSHOT = 'NO_SNAPSHOT_FOR_SUBJECT';

/** `true` quand le serveur dit n'avoir aucun snapshot à expliquer (404 typé). */
export function isNoSnapshotError(error: unknown): boolean {
  if (!isApiError(error) || error.status !== 404) {
    return false;
  }
  const body = error.detail;
  if (typeof body !== 'object' || body === null) {
    return true;
  }
  const detail = (body as { detail?: unknown }).detail;
  if (typeof detail === 'string') {
    return detail.includes(ERROR_NO_SNAPSHOT);
  }
  if (typeof detail === 'object' && detail !== null) {
    return (detail as { code?: unknown }).code === ERROR_NO_SNAPSHOT;
  }
  return true;
}

function ProviderBanner({
  provider,
  reason,
  templateAvailable,
  statusState,
}: {
  readonly provider: string | null;
  readonly reason: string | null;
  readonly templateAvailable: boolean | null;
  readonly statusState: string;
}) {
  return (
    <section
      className="vx-ai-provider"
      role="status"
      data-testid="ai-provider-banner"
      aria-labelledby="vx-ai-provider-title"
    >
      <p className="vx-badge vx-badge-warning" id="vx-ai-provider-title">
        {AI_PERMANENT_NOTICE}
      </p>
      <p className="vx-ai-provider-facts">
        <code>/ai/status</code> — état de la requête : <code>{statusState}</code> — fournisseur{' '}
        <code data-testid="ai-status-provider">{provider ?? 'non publié'}</code> — raison{' '}
        <code data-testid="ai-status-reason">{reason ?? 'non publiée'}</code> — gabarit
        déterministe disponible :{' '}
        <code>
          {templateAvailable === null ? 'non publié' : templateAvailable ? 'oui' : 'non'}
        </code>
      </p>
      <p className="vx-ai-provider-note">
        Ce bandeau n’est pas masquable : aucune phrase de cette page ne provient d’un modèle. Le
        gabarit déterministe explique un snapshot déjà certifié ; il ne lit aucune source, ne
        complète aucune donnée et ne rend aucun verdict.
      </p>
    </section>
  );
}

export function AiPage() {
  const [params, setParams] = useSearchParams();
  const kindParam = params.get('subject') ?? '';
  const kind: AiSubjectKind = isAiSubjectKind(kindParam) ? kindParam : 'analysis';
  const instrument = params.get('instrument') ?? DEV_SYNTHETIC_UNDERLYINGS[0] ?? '';

  const statusQuery = useAiStatus();
  const statusState = pageStateOf(statusQuery);
  const portfolioQuery = usePortfolio();
  const portfolioId = portfolioQuery.data?.portfolio.id ?? null;

  const key = kind === 'analysis' ? instrument : portfolioId === null ? '' : String(portfolioId);

  const answerQuery = useQuery<AiAnswer>({
    queryKey: ['ai', 'explain', kind, key] as const,
    queryFn: () => postAiExplain({ subject: { kind, key }, locale: 'fr' }),
    enabled: key !== '',
    retry: false,
    staleTime: Infinity,
  });
  const answerState = pageStateOf(answerQuery);
  const answer = answerQuery.data;
  const noSnapshot = isNoSnapshotError(answerQuery.error);

  function updateParam(name: string, value: string): void {
    const next = new URLSearchParams(params);
    next.set(name, value);
    setParams(next, { replace: true });
  }

  return (
    <article className="vx-ai" aria-labelledby="vx-page-title-ai">
      <header className="vx-page-header">
        <h1 id="vx-page-title-ai">Vertex IA</h1>
        <p className="vx-page-question">
          Comment expliquer, relier et résumer les données certifiées sans créer une seconde
          vérité ?
        </p>
      </header>

      <ProviderBanner
        provider={statusQuery.data?.provider ?? null}
        reason={statusQuery.data?.reason ?? null}
        templateAvailable={statusQuery.data?.deterministic_template_available ?? null}
        statusState={statusState}
      />

      <section className="vx-ai-subject" aria-labelledby="vx-ai-subject-title">
        <h2 id="vx-ai-subject-title">Sujet expliqué</h2>
        <div className="vx-matrix-filters">
          <label>
            Sujet
            <select
              name="subject"
              value={kind}
              onChange={(bubble) => updateParam('subject', bubble.target.value)}
            >
              {AI_SUBJECT_KINDS.map((entry) => (
                <option key={entry} value={entry}>
                  {AI_SUBJECT_LABELS[entry]}
                </option>
              ))}
            </select>
          </label>
          {kind === 'analysis' ? (
            <label>
              Instrument
              <select
                name="instrument"
                value={instrument}
                onChange={(bubble) => updateParam('instrument', bubble.target.value)}
              >
                {DEV_SYNTHETIC_UNDERLYINGS.map((entry) => (
                  <option key={entry} value={entry}>
                    {entry}
                  </option>
                ))}
              </select>
            </label>
          ) : null}
        </div>
        <p className="vx-ai-subject-note" data-testid="ai-subject-resource">
          Ressource expliquée : <code>{AI_SUBJECT_RESOURCE_LABELS[kind]}</code> — clé résolue :{' '}
          {key === '' ? (
            <span className="vx-cell-absent">
              aucun portefeuille déclaré n’a encore été lu : rien n’est expliqué
            </span>
          ) : (
            <code data-testid="ai-subject-key">{key}</code>
          )}
        </p>
      </section>

      {statusState === 'auth-required' || answerState === 'auth-required' ? (
        <AuthRequiredNotice />
      ) : noSnapshot ? (
        <DataStateBoundary
          state="empty"
          detail={
            'Aucun snapshot publié pour ce sujet (code NO_SNAPSHOT_FOR_SUBJECT) : il n’y a rien ' +
            'd’honnête à expliquer, et rien n’est inventé.'
          }
        />
      ) : key === '' ? (
        <DataStateBoundary
          state="empty"
          detail="Aucune clé de sujet résolue : le portefeuille déclaré n’a pas encore été lu."
        />
      ) : answer === undefined ? (
        <DataStateBoundary state={answerState as DataState} />
      ) : (
        <DataStateBoundary state={answerState as DataState}>
          {answer.state === 'refused' ? (
            <>
              <RefusalBlock answer={answer} />
              <MissingDataBlock answer={answer} />
              <LimitationsBlock answer={answer} />
              <TraceabilityBlock answer={answer} />
              <EvidenceCatalogBlock answer={answer} />
            </>
          ) : (
            <>
              <ClaimsBlock answer={answer} />
              <ExternalExcerptsBlock answer={answer} />
              <ContradictionsBlock answer={answer} />
              <MissingDataBlock answer={answer} />
              <LimitationsBlock answer={answer} />
              <TraceabilityBlock answer={answer} />
              <EvidenceCatalogBlock answer={answer} />
            </>
          )}
        </DataStateBoundary>
      )}

      <section className="vx-ai-note" aria-labelledby="vx-ai-note-title" data-testid="ai-note">
        <p className="vx-badge vx-badge-warning">{AI_NOTE_CAPABILITY_STATE}</p>
        <h2 id="vx-ai-note-title">Enregistrer une note à partir de cette explication</h2>
        <p>
          Capacité {AI_NOTE_CAPABILITY_STATE} : aucune route, aucun stockage et aucun exécuteur
          n’existent pour enregistrer une note issue de cette page. Rien n’est proposé en attente,
          et aucun formulaire n’est affiché.
        </p>
      </section>
    </article>
  );
}
