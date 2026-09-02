/**
 * `AbsentModule` — le socle de la phase « affichage d'abord ».
 *
 * POURQUOI CE COMPOSANT EXISTE. Les douze planches canoniques montrent des
 * modules dont environ la moitié n'a AUCUNE source dans ce dépôt. La consigne
 * est de livrer la composition d'abord et les branchements ensuite.
 *
 * Cet ordre n'est légitime qu'à une condition : un module non branché montre
 * sa GÉOMÉTRIE RÉELLE et déclare son absence avec un motif nommé — jamais un
 * chiffre inventé, jamais un rectangle gris muet. C'est l'article 17 de la
 * Constitution, et c'est aussi ce qui rend la phase 2 vérifiable : brancher,
 * c'est remplacer une absence NOMMÉE par une donnée relayée.
 *
 * Un rectangle gris sans motif serait pire qu'un module absent : il occuperait
 * la place sans dire pourquoi, et personne ne saurait s'il manque une source,
 * un abonnement ou une décision.
 */
import { render, screen, within } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { ABSENCE_REASONS, AbsentModule } from './AbsentModule.tsx';

describe('AbsentModule — une absence se NOMME, elle ne se devine pas', () => {
  it('rend le titre et la question du module, comme s’il était branché', () => {
    render(
      <AbsentModule
        title="Exposition aux facteurs"
        question="À quels facteurs le portefeuille est-il exposé ?"
        reason="NO_SOURCE"
      />,
    );
    // La place du module est TENUE : le lecteur voit ce qui devrait être là.
    expect(screen.getByRole('heading', { name: 'Exposition aux facteurs' })).toBeDefined();
    expect(
      screen.getByText('À quels facteurs le portefeuille est-il exposé ?'),
    ).toBeDefined();
  });

  it('affiche le MOTIF de l’absence, pas seulement l’absence', () => {
    const { rerender } = render(
      <AbsentModule title="T" question="Q" reason="NO_SOURCE" />,
    );
    expect(screen.getByText(ABSENCE_REASONS.NO_SOURCE.label)).toBeDefined();

    rerender(<AbsentModule title="T" question="Q" reason="SUBSCRIPTION_REQUIRED" />);
    expect(screen.getByText(ABSENCE_REASONS.SUBSCRIPTION_REQUIRED.label)).toBeDefined();

    rerender(<AbsentModule title="T" question="Q" reason="SERVER_CONTRACT_MISSING" />);
    expect(screen.getByText(ABSENCE_REASONS.SERVER_CONTRACT_MISSING.label)).toBeDefined();

    rerender(<AbsentModule title="T" question="Q" reason="DECISION_PENDING" />);
    expect(screen.getByText(ABSENCE_REASONS.DECISION_PENDING.label)).toBeDefined();
  });

  it('les quatre motifs sont DISTINCTS — aucun n’est le synonyme d’un autre', () => {
    // `financial-safety.md` : « réel, retardé, théorique, simulé et
    // démonstration ne partagent jamais le même statut visuel ou sémantique ».
    // La même exigence vaut pour les natures d'absence : « pas de source » et
    // « abonnement requis » n'appellent pas la même action.
    const labels = Object.values(ABSENCE_REASONS).map((entry) => entry.label);
    expect(new Set(labels).size).toBe(labels.length);
    const details = Object.values(ABSENCE_REASONS).map((entry) => entry.detail);
    expect(new Set(details).size).toBe(details.length);
  });

  it('n’affiche AUCUN chiffre — c’est l’invariant central', () => {
    const { container } = render(
      <AbsentModule
        title="VaR (95 %, 1 jour)"
        question="Quelle perte le portefeuille peut-il subir ?"
        reason="SERVER_CONTRACT_MISSING"
      />,
    );
    // Le titre peut contenir des chiffres (« 95 % », « 1 jour ») parce qu'il
    // décrit le module. Le CORPS, lui, ne doit porter aucune valeur.
    const corps = within(container).getByTestId('absent-body');
    expect(corps.textContent ?? '').not.toMatch(/\d/);
  });

  it('est annoncé aux lecteurs d’écran comme un état, pas comme une donnée', () => {
    render(<AbsentModule title="T" question="Q" reason="NO_SOURCE" />);
    const region = screen.getByRole('status');
    expect(region.getAttribute('data-absence')).toBe('NO_SOURCE');
  });

  it('accepte une précision propre au module, sans jamais l’inventer', () => {
    render(
      <AbsentModule
        title="Chaîne d’options"
        question="Quelle structure d’options le marché offre-t-il ?"
        reason="DECISION_PENDING"
        note="Le contrat de tranche exige taux et dividende : à trancher."
      />,
    );
    expect(
      screen.getByText('Le contrat de tranche exige taux et dividende : à trancher.'),
    ).toBeDefined();
  });
});
