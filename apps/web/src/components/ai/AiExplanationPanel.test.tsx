/**
 * Page Vertex IA — invariants testés :
 * - le bandeau B-05 est permanent, non masquable, et `/ai/status` est affiché ;
 * - un refus (`state = "refused"`) est rendu comme un REFUS explicite avec sa
 *   raison, jamais comme une explication vide ;
 * - les extraits externes vivent dans un bloc distinct, étiqueté
 *   « Contenu externe non vérifié », séparé des affirmations, et leur texte
 *   n'est jamais réinjecté en HTML brut ;
 * - les citations sont ouvrables vers l'entrée du catalogue de preuves ;
 * - la traçabilité (`snapshot_version`, `content_hash`, `as_of`) est visible ;
 * - l'enregistrement d'une note est déclaré NON_IMPLÉMENTÉ.
 */
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { ApiError } from '../../api/client.ts';
import {
  makeAiAnswer,
  makeAnalysis,
  makeMarketsOverview,
  makePortfolioResponse,
  makeRefusedAiAnswer,
} from '../../test/fixtures.ts';
import { renderApp } from '../../test/render.tsx';
import { isNoSnapshotError } from './AiExplanationPanel.tsx';
import { isWellFormedAnswer } from './aiView.ts';
import {
  AI_PERMANENT_NOTICE,
  evidenceAnchorId,
  evidenceIndexOf,
  evidenceLabelOf,
  isAiSubjectKind,
  isRefusal,
} from './aiView.ts';

const fetchMock = vi.fn<typeof fetch>();

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  });
}


beforeEach(() => {
  vi.stubGlobal('fetch', fetchMock);
  fetchMock.mockReset();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

interface AiHandlers {
  readonly explain?: (body: unknown) => Response;
  readonly status?: () => Response;
}

function mockAi(handlers: AiHandlers = {}): void {
  fetchMock.mockImplementation(async (input, init) => {
    const url = String(input);
    const body = typeof init?.body === 'string' ? (JSON.parse(init.body) as unknown) : undefined;
    if (url.endsWith('/v1/ai/status')) {
      return (
        handlers.status?.() ??
        jsonResponse({
          provider: 'DISABLED',
          reason: 'B-05_HUMAN_DECISION_PENDING',
          deterministic_template_available: true,
        })
      );
    }
    if (url.endsWith('/v1/ai/explain')) {
      return handlers.explain?.(body) ?? jsonResponse(makeAiAnswer());
    }
    if (url.endsWith('/v1/portfolio')) {
      return jsonResponse(makePortfolioResponse());
    }
    if (url.endsWith('/v1/markets/overview')) {
      // Le sélecteur d'instruments lit l'univers RÉELLEMENT publié.
      return jsonResponse(makeMarketsOverview());
    }
    // Le panneau n'est monté QUE lorsque la page hôte a chargé son dossier.
    // Sans cette route, Analyse reste en erreur et le panneau n'apparaît
    // jamais.
    //
    // Cette route manquait, et la CI l'a attrapé. Le test avait été écrit
    // quand le panneau était monté HORS de la branche « dossier chargé » : il
    // passait alors légitimement. Déplacer le montage à l'intérieur de cette
    // branche l'a invalidé, et la suite unitaire n'a pas été relancée après ce
    // déplacement — seule la campagne e2e l'a été. Ce n'était donc pas un test
    // instable : il échouait de façon parfaitement reproductible, 3 fois sur 3
    // en isolation.
    if (url.includes('/v1/analysis/')) {
      return jsonResponse(makeAnalysis());
    }
    return jsonResponse({ detail: 'unexpected route' }, 500);
  });
}

// LOT-12 : l'explication n'est plus une destination. C'est un panneau de
// l'inspecteur, monté par les pages qui portent un dossier explicable. Les
// assertions ci-dessous sont INCHANGÉES — c'est leur rôle : prouver que
// l'absorption n'a retiré aucune capacité (règle 1 de l'arbitrage).
//
// `/portfolio` est la page hôte par défaut ici : elle porte DEUX dossiers
// explicables (valorisation et performance), donc elle exerce aussi le choix
// entre dossiers.
async function renderAi(path = '/portfolio'): Promise<void> {
  renderApp(path);
  await screen.findByRole('heading', { level: 2, name: /^Inspecteur/ });
}

describe('aiView — aides pures', () => {
  it('reconnaît les trois sujets du contrat et rien d’autre', () => {
    expect(isAiSubjectKind('analysis')).toBe(true);
    expect(isAiSubjectKind('portfolio_valuation')).toBe(true);
    expect(isAiSubjectKind('performance')).toBe(true);
    expect(isAiSubjectKind('portefeuille')).toBe(false);
  });

  it('fabrique une ancre HTML stable et résout une citation', () => {
    expect(evidenceAnchorId('sha256:ab/cd')).toBe('vx-ai-evidence-sha256-ab-cd');
    const index = evidenceIndexOf(makeAiAnswer().evidence_catalog);
    expect(evidenceLabelOf('sha256:b41f', index)).toBe('news_cluster · evidence.clusters[]');
    expect(evidenceLabelOf('inconnue', index)).toContain('hors catalogue');
  });

  it('distingue un refus d’une réponse produite', () => {
    expect(isRefusal(makeRefusedAiAnswer())).toBe(true);
    expect(isRefusal(makeAiAnswer())).toBe(false);
  });

  it('reconnaît le 404 typé « aucun snapshot pour ce sujet »', () => {
    expect(
      isNoSnapshotError(new ApiError('HTTP', 'x', 404, { detail: { code: 'NO_SNAPSHOT_FOR_SUBJECT' } })),
    ).toBe(true);
    expect(isNoSnapshotError(new ApiError('HTTP', 'x', 500))).toBe(false);
    expect(isNoSnapshotError(new ApiError('NETWORK', 'x'))).toBe(false);
  });
});

describe('page Vertex IA — rendu', () => {
  it('affiche le bandeau permanent B-05 et l’état de /ai/status', async () => {
    mockAi();
    await renderAi();
    const banner = await screen.findByTestId('ai-provider-banner');
    expect(banner.textContent).toContain(AI_PERMANENT_NOTICE);
    await waitFor(() => {
      expect(screen.getByTestId('ai-status-provider').textContent).toBe('DISABLED');
    });
    expect(screen.getByTestId('ai-status-reason').textContent).toBe('B-05_HUMAN_DECISION_PENDING');
    // Aucun contrôle ne permet de masquer le bandeau.
    expect(within(banner).queryByRole('button')).toBeNull();
  });

  it('la première limite reste l’avis B-05', async () => {
    mockAi();
    await renderAi();
    const limitations = await screen.findByTestId('ai-limitations');
    const first = within(limitations).getAllByRole('listitem')[0];
    expect(first?.textContent).toContain('décision B-05 en attente');
    expect(first?.getAttribute('data-first')).toBe('true');
  });

  it('rend un refus comme un REFUS explicite, jamais une explication vide', async () => {
    mockAi({ explain: () => jsonResponse(makeRefusedAiAnswer()) });
    await renderAi();
    const refusal = await screen.findByTestId('ai-refusal');
    expect(refusal.getAttribute('data-state')).toBe('refused');
    expect(refusal.textContent).toContain('REFUS');
    expect(screen.getByTestId('ai-refusal-reason').textContent).toContain(
      'empty or unusable corpus',
    );
    // Aucun bloc d'affirmations vide n'est affiché à la place du refus.
    expect(screen.queryByTestId('ai-claims')).toBeNull();
    expect(screen.queryByTestId('ai-external')).toBeNull();
    // La traçabilité reste visible même en refus.
    expect(screen.getByTestId('ai-content-hash').textContent).toBe('sha256:dcd5');
  });

  it('isole les extraits externes et rend leur texte échappé comme du TEXTE', async () => {
    mockAi();
    await renderAi();
    const external = await screen.findByTestId('ai-external');
    const claims = screen.getByTestId('ai-claims');
    expect(external.contains(claims)).toBe(false);
    expect(claims.contains(external)).toBe(false);
    expect(external.textContent).toContain('Contenu externe non vérifié');
    const quote = within(external).getByTestId('ai-external-quote');
    // Le serveur a déjà échappé : la chaîne est affichée telle quelle et
    // AUCUN élément <script> n'existe dans le DOM rendu.
    expect(quote.textContent).toContain('&lt;script&gt;alert(1)&lt;/script&gt;');
    expect(quote.querySelector('script')).toBeNull();
    expect(document.querySelectorAll('script').length).toBe(0);
    // L'extrait n'est jamais mêlé aux affirmations.
    expect(claims.textContent).not.toContain('alert(1)');
    expect(external.textContent).toContain('EXTERNAL_UNVERIFIED');
  });

  it('les citations sont ouvrables vers l’entrée du catalogue', async () => {
    mockAi();
    await renderAi();
    const link = await screen.findByTestId('ai-claim-ref-snapshot:analysis/SYN-TECH-01/v16');
    const anchor = evidenceAnchorId('snapshot:analysis/SYN-TECH-01/v16');
    expect(link.getAttribute('href')).toBe(`#${anchor}`);
    const target = screen.getByTestId('ai-evidence-snapshot:analysis/SYN-TECH-01/v16');
    expect(target.getAttribute('id')).toBe(anchor);
    expect(target.textContent).toContain('analysis/SYN-TECH-01');
  });

  it('affiche contradictions, données manquantes et traçabilité complète', async () => {
    mockAi();
    await renderAi();
    expect((await screen.findByTestId('ai-contradictions')).textContent).toContain(
      'entitlements_sufficient',
    );
    expect(screen.getByTestId('ai-missing').textContent).toContain('UNEVALUABLE');
    expect(screen.getByTestId('ai-snapshot-version').textContent).toBe('16');
    expect(screen.getByTestId('ai-content-hash').textContent).toBe('sha256:dcd5');
    expect(screen.getByTestId('ai-as-of').textContent).toBe('2026-08-25T12:00:00+00:00');
    expect(screen.getByTestId('ai-answer-provider').textContent).toBe('DETERMINISTIC_TEMPLATE');
  });

  it('déclare l’enregistrement d’une note NON_IMPLÉMENTÉ, sans formulaire', async () => {
    mockAi();
    await renderAi();
    const note = await screen.findByTestId('ai-note');
    expect(note.textContent).toContain('NON_IMPLÉMENTÉ');
    expect(within(note).queryByRole('button')).toBeNull();
    expect(within(note).queryByRole('textbox')).toBeNull();
  });

  it('change de dossier et envoie la clé résolue du portefeuille déclaré', async () => {
    // Invariant INCHANGÉ : le panneau envoie au serveur la clé RÉSOLUE, jamais
    // un identifiant deviné, et changer de dossier change le sujet envoyé.
    // Seul le libellé du contrôle change : il ne propose plus que les dossiers
    // que la page hôte affiche réellement.
    const subjects: unknown[] = [];
    mockAi({
      explain: (body) => {
        subjects.push((body as { subject?: unknown }).subject);
        return jsonResponse(makeAiAnswer());
      },
    });
    await renderAi();
    await screen.findByTestId('ai-claims');

    // Dossier par défaut : le premier que la page porte.
    await waitFor(() => {
      expect(subjects).toContainEqual({ kind: 'portfolio_valuation', key: '1' });
    });

    const user = userEvent.setup();
    await user.selectOptions(screen.getByRole('combobox', { name: 'Dossier' }), 'performance');
    await waitFor(() => {
      expect(screen.getByTestId('ai-subject-key').textContent).toBe('1');
    });
    await waitFor(() => {
      expect(subjects).toContainEqual({ kind: 'performance', key: '1' });
    });
  });

  it('ne propose QUE les dossiers que la page hôte affiche réellement', async () => {
    // L'ancienne page laissait choisir un sujet qu'aucune page n'affichait.
    // Portefeuille porte la valorisation et la performance — pas l'analyse
    // d'un instrument, qui appartient à une autre destination.
    mockAi();
    await renderAi();
    const choix = await screen.findByRole('combobox', { name: 'Dossier' });
    const options = Array.from(choix.querySelectorAll('option')).map((entry) => entry.value);
    expect(options).toEqual(['portfolio_valuation', 'performance']);
    expect(options).not.toContain('analysis');
  });

  it('une page à dossier unique n’affiche AUCUN sélecteur', async () => {
    // Analyse ne porte qu'un dossier : proposer un choix d'un seul élément
    // serait un contrôle sans décision, que `.claude/rules/frontend.md`
    // interdit.
    mockAi();
    renderApp('/analysis/SYN-TECH-01');
    // LOT-A4 : Analyse monte aussi l'inspecteur du dossier ; c'est le panneau
    // d'EXPLICATION qui est attendu ici.
    await screen.findByRole('heading', { level: 2, name: /^Inspecteur — explication/ });
    expect(screen.queryByRole('combobox', { name: 'Dossier' })).toBeNull();
    await waitFor(() => {
      expect(screen.getByTestId('ai-subject-key').textContent).toBe('SYN-TECH-01');
    });
  });

  it('un 404 typé devient un état vide honnête, jamais une explication inventée', async () => {
    mockAi({
      explain: () => jsonResponse({ detail: { code: 'NO_SNAPSHOT_FOR_SUBJECT' } }, 404),
    });
    await renderAi();
    await waitFor(() => {
      expect(screen.getByText('Aucune donnée')).toBeDefined();
    });
    // Le sujet par défaut vient désormais de l univers RÉELLEMENT publié,
    // donc d une requête : on ATTEND le code, on ne l exige pas au premier
    // rendu. L exigence elle-même est inchangée.
    expect(await screen.findByText(/NO_SNAPSHOT_FOR_SUBJECT/)).toBeDefined();
    expect(screen.queryByTestId('ai-claims')).toBeNull();
  });
});

describe('garde de forme — une explication ne doit jamais emporter sa page hôte', () => {
  it('reconnaît une réponse conforme et refuse toute forme incomplète', () => {
    expect(isWellFormedAnswer(makeAiAnswer())).toBe(true);
    expect(isWellFormedAnswer(null)).toBe(false);
    expect(isWellFormedAnswer('refused')).toBe(false);
    expect(isWellFormedAnswer({})).toBe(false);
    // Chacune des six listes du contrat suffit à invalider la réponse.
    for (const champ of [
      'claims',
      'contradictions',
      'evidence_catalog',
      'external_excerpts',
      'limitations',
      'missing_data',
    ]) {
      const tronquee: Record<string, unknown> = { ...makeAiAnswer() };
      delete tronquee[champ];
      expect(isWellFormedAnswer(tronquee), `${champ} manquant doit invalider`).toBe(false);
    }
  });

  it('une réponse hors contrat donne un état error, et la page hôte survit', async () => {
    // Reproduit le défaut trouvé en absorbant /ai : une page hôte servant un
    // corps d'une AUTRE ressource faisait planter ClaimsBlock sur
    // « catalog is not iterable », et l'erreur emportait la route entière.
    mockAi({ explain: () => jsonResponse({ state: 'ok', claims: [] }) });
    await renderAi();
    await waitFor(() => {
      expect(document.querySelector('[data-state="error"]')).not.toBeNull();
    });
    expect(screen.queryByTestId('ai-claims')).toBeNull();
    // La page hôte est TOUJOURS là : c'est la propriété qui compte.
    expect(screen.getByRole('heading', { level: 1, name: 'Portefeuille' })).toBeDefined();
  });
});
