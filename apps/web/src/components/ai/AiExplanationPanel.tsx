import { useQuery } from '@tanstack/react-query';
import { useSearchParams } from 'react-router-dom';

import { isApiError } from '../../api/client.ts';
import type { AiAnswer } from '../../api/client.ts';
import { postAiExplain, useAiStatus } from '../../api/decisionApi.ts';
import { pageStateOf } from '../../api/hooks.ts';
import { AuthRequiredNotice } from '../AuthRequiredNotice.tsx';
import { DataStateBoundary } from '../DataStateBoundary.tsx';
import type { DataState } from '../DataStateBoundary.tsx';
import { InspectorPanel } from '../../shell/inspector.tsx';
import {
  AI_NOTE_CAPABILITY_STATE,
  AI_PERMANENT_NOTICE,
  AI_SUBJECT_LABELS,
  AI_SUBJECT_RESOURCE_LABELS,
  isAiSubjectKind,
  isWellFormedAnswer,
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
 * Explication IA — panneau d'INSPECTEUR, plus une destination.
 *
 * Question conservée : « Comment expliquer, relier et résumer les données
 * certifiées sans créer une seconde vérité ? »
 *
 * Absorbé depuis `/ai` au LOT-12, d'après `docs/05-design/PAGE_ARBITRATION.md` :
 * « l'IA explique le dossier ouvert, donc elle vit dans l'inspecteur ». Le
 * contrat serveur ne connaît que TROIS sujets — `analysis/<instrument>`,
 * `portfolio_valuation/<portefeuille>` et `performance/<portefeuille>` — qui
 * sont exactement les dossiers d'Analyse et de Portefeuille. L'absorption est
 * donc mécanique : la page HÔTE dit quel dossier est ouvert, ce composant
 * l'explique.
 *
 * Ce qui a disparu, et pourquoi : le sélecteur de sujet. Il laissait choisir
 * un sujet qu'aucune page n'affichait — l'inverse d'« expliquer le dossier
 * ouvert ». Les sujets proposés sont désormais ceux que la page hôte porte
 * RÉELLEMENT, et rien d'autre.
 *
 * La route API `/v1/ai/explain` et `/v1/ai/status` ne bougent pas (règle 2).
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

/** Un dossier que la page hôte affiche réellement et sait faire expliquer. */
export interface AiDossier {
  readonly kind: AiSubjectKind;
  /** Clé du sujet. Vide = la page n'a pas encore résolu son dossier. */
  readonly key: string;
}

export interface AiExplanationPanelProps {
  /**
   * Dossiers ouverts sur la page hôte, dans l'ordre d'affichage. Le premier
   * est expliqué par défaut. Une liste vide ne monte AUCUN panneau : sans
   * dossier ouvert, il n'y a rien à expliquer.
   */
  readonly dossiers: readonly AiDossier[];
}

export function AiExplanationPanel({ dossiers }: AiExplanationPanelProps) {
  // Le sujet expliqué vit dans l'URL : il survit à un rechargement et rend le
  // dossier expliqué partageable, comme l'ancienne page le faisait.
  const [params, setParams] = useSearchParams();
  const kindParam = params.get('explain') ?? '';
  const chosen =
    isAiSubjectKind(kindParam) && dossiers.some((entry) => entry.kind === kindParam)
      ? kindParam
      : (dossiers[0]?.kind ?? null);
  const dossier = dossiers.find((entry) => entry.kind === chosen) ?? null;

  const statusQuery = useAiStatus();
  const statusState = pageStateOf(statusQuery);

  const kind: AiSubjectKind = dossier?.kind ?? 'analysis';
  const key = dossier?.key ?? '';

  const answerQuery = useQuery<AiAnswer>({
    queryKey: ['ai', 'explain', kind, key] as const,
    queryFn: () => postAiExplain({ subject: { kind, key }, locale: 'fr' }),
    enabled: key !== '',
    retry: false,
    staleTime: Infinity,
  });
  const answerState = pageStateOf(answerQuery);
  //: L'API ne repond pas : ni `ok`, ni `loading`. Un sujet non resolu
  //: dans cet etat est une panne, jamais une absence.
  const statusIndisponible = statusState === 'offline' || statusState === 'error';
  const answer = answerQuery.data;
  const noSnapshot = isNoSnapshotError(answerQuery.error);

  function updateParam(name: string, value: string): void {
    const next = new URLSearchParams(params);
    next.set(name, value);
    setParams(next, { replace: true });
  }

  // Sans dossier ouvert, aucun panneau n'est monté : l'inspecteur reste libre
  // (règle « aucune colonne morte » du LOT-11).
  if (dossier === null) {
    return null;
  }

  return (
    <InspectorPanel subject="explication">
      <p className="vx-page-question">
        Comment expliquer, relier et résumer les données certifiées sans créer une seconde
        vérité ?
      </p>

      <ProviderBanner
        provider={statusQuery.data?.provider ?? null}
        reason={statusQuery.data?.reason ?? null}
        templateAvailable={statusQuery.data?.deterministic_template_available ?? null}
        statusState={statusState}
      />

      <section className="vx-ai-subject" aria-labelledby="vx-ai-subject-title">
        <h3 id="vx-ai-subject-title">Dossier expliqué</h3>
        {/*
          Le choix ne porte QUE sur les dossiers que la page hôte affiche
          réellement. Un dossier absent de la page n'est pas proposé : on
          explique ce qui est ouvert, jamais ce qui ne l'est pas. Un seul
          dossier ouvert = aucun choix à faire, donc aucun contrôle affiché.
        */}
        {dossiers.length > 1 ? (
          <div className="vx-matrix-filters">
            <label>
              Dossier
              <select
                name="explain"
                value={kind}
                onChange={(bubble) => updateParam('explain', bubble.target.value)}
              >
                {dossiers.map((entry) => (
                  <option key={entry.kind} value={entry.kind}>
                    {AI_SUBJECT_LABELS[entry.kind]}
                  </option>
                ))}
              </select>
            </label>
          </div>
        ) : null}
        <p className="vx-ai-subject-note" data-testid="ai-subject-resource">
          Ressource expliquée : <code>{AI_SUBJECT_RESOURCE_LABELS[kind]}</code> — clé résolue :{' '}
          {key === '' ? (
            <span className="vx-cell-absent">
              le dossier de cette page n’est pas encore résolu : rien n’est expliqué
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
      ) : key === '' && statusIndisponible ? (
        // Une clé non résolue PARCE QUE l'API est injoignable n'est pas une
        // absence. Le sujet par défaut vient de l'univers réellement publié,
        // donc d'une requête : hors ligne, elle échoue. Afficher « vide » ici
        // ferait passer une panne pour un état normal.
        <DataStateBoundary state={statusState as DataState} />
      ) : key === '' ? (
        <DataStateBoundary
          state="empty"
          detail="Aucune clé de sujet résolue : le dossier de cette page n’a pas encore été lu."
        />
      ) : answer === undefined ? (
        <DataStateBoundary state={answerState as DataState} />
      ) : !isWellFormedAnswer(answer) ? (
        // Réponse hors contrat : l'explication est refusée en bloc plutôt que
        // rendue à moitié. Ce panneau vit DANS une page qui porte un dossier
        // financier — il ne doit jamais emporter son hôte en échouant.
        <DataStateBoundary
          state="error"
          detail={
            'Réponse d’explication hors contrat (listes attendues absentes) — rien n’est ' +
            'affiché à la place, et le dossier de la page reste intact.'
          }
        />
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
        <h3 id="vx-ai-note-title">Enregistrer une note à partir de cette explication</h3>
        <p>
          Capacité {AI_NOTE_CAPABILITY_STATE} : aucune route, aucun stockage et aucun exécuteur
          n’existent pour enregistrer une note. Rien n’est proposé en attente, et aucun
          formulaire n’est affiché.
        </p>
      </section>
    </InspectorPanel>
  );
}
