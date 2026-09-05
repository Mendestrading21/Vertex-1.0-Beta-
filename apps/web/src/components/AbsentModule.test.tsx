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

  it('montre le motif COURT, et range le reste derrière « Pourquoi ? »', () => {
    // La divulgation progressive n'a de valeur que si elle divulgue vraiment :
    // le motif court doit être visible SANS interaction, et l'explication
    // complète doit être atteignable AVEC une interaction — pas supprimée.
    render(
      <AbsentModule
        title="Structure de volatilité"
        question="Comment la volatilité implicite évolue-t-elle par échéance ?"
        reason="NO_SOURCE"
        note="Aucune surface en terme de volatilité n’est publiée."
      />,
    );
    const corps = screen.getByTestId('absent-body');
    const details = corps.querySelector('details');
    expect(details, 'l’explication doit vivre dans un élément de divulgation').not.toBeNull();
    // Le motif court est HORS du repli : c'est ce qu'on lit sans rien ouvrir.
    const court = corps.querySelector('.vx-absent-court');
    expect(court?.textContent).toBe(ABSENCE_REASONS.NO_SOURCE.court);
    expect(details!.contains(court!)).toBe(false);
    // Et il est nettement plus court que l'explication qu'il résume, sinon la
    // divulgation ne gagne rien.
    expect(ABSENCE_REASONS.NO_SOURCE.court.length).toBeLessThan(
      ABSENCE_REASONS.NO_SOURCE.detail.length / 2,
    );
    // Question, détail et note restent dans le document, repliés.
    for (const attendu of [
      'Comment la volatilité implicite évolue-t-elle par échéance ?',
      ABSENCE_REASONS.NO_SOURCE.detail,
      'Aucune surface en terme de volatilité n’est publiée.',
    ]) {
      expect(details!.textContent).toContain(attendu);
    }
    // Le repli s'ouvre par un contrôle NOMMÉ, pas par un clic sur du vide.
    expect(details!.querySelector('summary')?.textContent?.trim()).toContain('Pourquoi');
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
    // Le motif court est ce qui reste à l'écran : c'est LUI qui doit
    // distinguer les quatre natures, sans quoi la carte repliée les confond.
    const courts = Object.values(ABSENCE_REASONS).map((entry) => entry.court);
    expect(new Set(courts).size).toBe(courts.length);
    for (const court of courts) {
      expect(court.length, `motif court trop long : ${court}`).toBeLessThanOrEqual(48);
    }
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
