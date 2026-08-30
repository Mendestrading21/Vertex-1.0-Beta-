import type { AiAnswer } from '../../api/client.ts';
import { evidenceAnchorId, evidenceIndexOf, evidenceLabelOf } from './aiView.ts';

/**
 * Rendu de la réponse déterministe. Trois séparations sont structurelles :
 *
 * 1. un REFUS (`state = "refused"`) n'est jamais rendu comme une explication
 *    vide : il occupe son propre bloc, porte le mot « REFUS » et sa raison ;
 * 2. les affirmations citent leurs preuves par des liens OUVRABLES vers
 *    l'entrée correspondante du catalogue (ancre stable) ;
 * 3. les extraits externes vivent dans un bloc visuellement DISTINCT étiqueté
 *    « Contenu externe non vérifié ». Le texte arrive déjà échappé par le
 *    serveur et il est rendu comme du TEXTE React — jamais réinjecté en HTML
 *    brut (aucun `dangerouslySetInnerHTML` dans ce fichier ni dans la page).
 */

export function RefusalBlock({ answer }: { readonly answer: AiAnswer }) {
  return (
    <section
      className="vx-ai-refusal"
      role="alert"
      data-state="refused"
      data-testid="ai-refusal"
      aria-labelledby="vx-ai-refusal-title"
    >
      <p className="vx-badge vx-badge-warning">REFUS — AUCUNE EXPLICATION PRODUITE</p>
      <h2 id="vx-ai-refusal-title">Explication refusée</h2>
      <p className="vx-ai-refusal-reason" data-testid="ai-refusal-reason">
        Raison du refus : {answer.refusal_reason ?? 'aucune raison publiée par le serveur'}
      </p>
      <p>
        Le corpus servi est vide ou inexploitable. Aucune affirmation n’est produite : un refus
        n’est pas une explication incomplète, et rien n’est comblé.
      </p>
    </section>
  );
}

export function ClaimsBlock({ answer }: { readonly answer: AiAnswer }) {
  const index = evidenceIndexOf(answer.evidence_catalog);
  return (
    <section className="vx-ai-claims" aria-labelledby="vx-ai-claims-title" data-testid="ai-claims">
      <h2 id="vx-ai-claims-title">Affirmations sourcées</h2>
      {answer.claims.length === 0 ? (
        <p className="vx-cell-absent">Aucune affirmation publiée.</p>
      ) : (
        <ol className="vx-ai-claim-list">
          {answer.claims.map((claim, position) => (
            <li
              // La liste arrive entière dans un DTO, est remplacée en bloc et n'est jamais triée, filtrée ni insérée côté client : aucun
              // réordonnancement local n'est possible. L'index seul serait insuffisant ; le contenu seul pourrait se répéter.
              // biome-ignore lint/suspicious/noArrayIndexKey: la clé n'est PAS l'index seul, elle concatène l'index ET le contenu publié par le serveur.
              key={`${position}-${claim.text}`}
              className="vx-ai-claim"
            >
              <p className="vx-ai-claim-text">{claim.text}</p>
              <p className="vx-ai-claim-refs">
                <span className="vx-ai-claim-kind">
                  <span aria-hidden="true">◆</span> {claim.kind}
                </span>{' '}
                — preuves :{' '}
                {claim.evidence_refs.map((reference, refPosition) => (
                  <span key={reference}>
                    {refPosition > 0 ? ', ' : null}
                    <a
                      className="vx-ai-claim-ref"
                      href={`#${evidenceAnchorId(reference)}`}
                      data-testid={`ai-claim-ref-${reference}`}
                      title={evidenceLabelOf(reference, index)}
                    >
                      <code>{reference}</code>
                    </a>
                  </span>
                ))}
              </p>
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}

export function ExternalExcerptsBlock({ answer }: { readonly answer: AiAnswer }) {
  return (
    <section
      className="vx-ai-external"
      aria-labelledby="vx-ai-external-title"
      data-testid="ai-external"
    >
      <p className="vx-badge vx-badge-warning">CONTENU EXTERNE NON VÉRIFIÉ</p>
      <h2 id="vx-ai-external-title">Contenu externe non vérifié</h2>
      <p className="vx-ai-external-note">
        Matériau de source cité tel quel, hors des affirmations Vertex. Il n’est ni une donnée
        certifiée, ni un fait, ni une consigne. Le serveur l’a déjà neutralisé et tronqué ; il est
        affiché ici comme du texte, jamais interprété comme du balisage.
      </p>
      {answer.external_excerpts.length === 0 ? (
        <p className="vx-cell-absent" data-testid="ai-external-empty">
          Aucun extrait externe dans cette réponse.
        </p>
      ) : (
        <ul className="vx-ai-external-list">
          {answer.external_excerpts.map((excerpt, position) => (
            <li
              // La liste arrive entière dans un DTO, est remplacée en bloc et n'est jamais triée, filtrée ni insérée côté client : aucun
              // réordonnancement local n'est possible. L'index seul serait insuffisant ; le contenu seul pourrait se répéter.
              // biome-ignore lint/suspicious/noArrayIndexKey: la clé n'est PAS l'index seul, elle concatène l'index ET le contenu publié par le serveur.
              key={`${position}-${excerpt.evidence_ref}`}
              className="vx-ai-external-item"
              data-testid={`ai-external-${excerpt.evidence_ref}`}
            >
              <p className="vx-ai-external-label">
                <span aria-hidden="true">⚠</span> <code>{excerpt.label}</code>
                {excerpt.truncated ? <span> — extrait tronqué par le serveur</span> : null}
              </p>
              <blockquote className="vx-ai-external-quote" data-testid="ai-external-quote">
                {excerpt.excerpt}
              </blockquote>
              <p className="vx-ai-external-ref">
                Preuve associée :{' '}
                <a href={`#${evidenceAnchorId(excerpt.evidence_ref)}`}>
                  <code>{excerpt.evidence_ref}</code>
                </a>
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function ContradictionsBlock({ answer }: { readonly answer: AiAnswer }) {
  return (
    <section
      className="vx-ai-contradictions"
      aria-labelledby="vx-ai-contradictions-title"
      data-testid="ai-contradictions"
    >
      <h2 id="vx-ai-contradictions-title">Contradictions relevées</h2>
      {answer.contradictions.length === 0 ? (
        <p className="vx-cell-absent">Aucune contradiction publiée.</p>
      ) : (
        <ul>
          {answer.contradictions.map((contradiction, position) => (
            <li
              // La liste arrive entière dans un DTO, est remplacée en bloc et n'est jamais triée, filtrée ni insérée côté client : aucun
              // réordonnancement local n'est possible. L'index seul serait insuffisant ; le contenu seul pourrait se répéter.
              // biome-ignore lint/suspicious/noArrayIndexKey: la clé n'est PAS l'index seul, elle concatène l'index ET le contenu publié par le serveur.
              key={`${position}-${contradiction.code}`}
            >
              <span aria-hidden="true">✕</span> {contradiction.text} — code{' '}
              <code>{contradiction.code}</code>
              {contradiction.reference !== null ? (
                <>
                  {' '}
                  — référence <code>{contradiction.reference}</code>
                </>
              ) : null}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function MissingDataBlock({ answer }: { readonly answer: AiAnswer }) {
  return (
    <section className="vx-ai-missing" aria-labelledby="vx-ai-missing-title" data-testid="ai-missing">
      <h2 id="vx-ai-missing-title">Données manquantes</h2>
      {answer.missing_data.length === 0 ? (
        <p className="vx-cell-absent">Aucune donnée déclarée manquante.</p>
      ) : (
        <ul>
          {answer.missing_data.map((entry, position) => (
            <li
              // La liste arrive entière dans un DTO, est remplacée en bloc et n'est jamais triée, filtrée ni insérée côté client : aucun
              // réordonnancement local n'est possible. L'index seul serait insuffisant ; le contenu seul pourrait se répéter.
              // biome-ignore lint/suspicious/noArrayIndexKey: la clé n'est PAS l'index seul, elle concatène l'index ET le contenu publié par le serveur.
              key={`${position}-${entry}`}
            >
              <span aria-hidden="true">⊘</span> {entry}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function LimitationsBlock({ answer }: { readonly answer: AiAnswer }) {
  return (
    <section
      className="vx-ai-limitations"
      aria-labelledby="vx-ai-limitations-title"
      data-testid="ai-limitations"
    >
      <h2 id="vx-ai-limitations-title">Limites</h2>
      <ol className="vx-ai-limitation-list">
        {answer.limitations.map((limitation, position) => (
          <li
            // La liste arrive entière dans un DTO, est remplacée en bloc et n'est jamais triée, filtrée ni insérée côté client : aucun
            // réordonnancement local n'est possible. L'index seul serait insuffisant ; le contenu seul pourrait se répéter.
            // biome-ignore lint/suspicious/noArrayIndexKey: la clé n'est PAS l'index seul, elle concatène l'index ET le contenu publié par le serveur.
            key={`${position}-${limitation}`}
            data-first={String(position === 0)}
          >
            {limitation}
          </li>
        ))}
      </ol>
    </section>
  );
}

export function EvidenceCatalogBlock({ answer }: { readonly answer: AiAnswer }) {
  return (
    <section
      className="vx-ai-catalog"
      aria-labelledby="vx-ai-catalog-title"
      data-testid="ai-catalog"
    >
      <h2 id="vx-ai-catalog-title">Catalogue des preuves</h2>
      <div className="vx-matrix-scroll" tabIndex={0} role="region" aria-labelledby="vx-ai-catalog-title">
        <table className="vx-matrix-table">
          <caption>
            Chaque citation d’une affirmation renvoie à une ligne de ce catalogue, publié par le
            serveur avec le chemin exact de la preuve dans le snapshot.
          </caption>
          <thead>
            <tr>
              <th scope="col">Identifiant de preuve</th>
              <th scope="col">Type</th>
              <th scope="col">Chemin dans le snapshot</th>
            </tr>
          </thead>
          <tbody>
            {answer.evidence_catalog.map((entry) => (
              <tr
                key={entry.evidence_id}
                id={evidenceAnchorId(entry.evidence_id)}
                data-testid={`ai-evidence-${entry.evidence_id}`}
                tabIndex={-1}
              >
                <th scope="row">
                  <code>{entry.evidence_id}</code>
                </th>
                <td>
                  <code>{entry.evidence_type}</code>
                </td>
                <td>
                  <code>{entry.path}</code>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export function TraceabilityBlock({ answer }: { readonly answer: AiAnswer }) {
  return (
    <dl className="vx-ai-trace" data-testid="ai-trace">
      <div>
        <dt>Fournisseur</dt>
        <dd>
          <code data-testid="ai-answer-provider">{answer.provider}</code>
        </dd>
      </div>
      <div>
        <dt>Gabarit</dt>
        <dd>
          <code>{answer.template_version}</code>
        </dd>
      </div>
      <div>
        <dt>Sujet</dt>
        <dd>
          <code>
            {answer.subject.kind}/{answer.subject.key}
          </code>
        </dd>
      </div>
      <div>
        <dt>Version du snapshot</dt>
        <dd className="vx-num" data-testid="ai-snapshot-version">
          {answer.snapshot_version}
        </dd>
      </div>
      <div>
        <dt>Empreinte du contenu</dt>
        <dd>
          <code data-testid="ai-content-hash">{answer.content_hash}</code>
        </dd>
      </div>
      <div>
        <dt>as_of</dt>
        <dd>
          <time dateTime={answer.as_of} data-testid="ai-as-of">
            {answer.as_of}
          </time>
        </dd>
      </div>
    </dl>
  );
}
