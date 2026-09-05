import type { ReactNode } from 'react';

/**
 * MÉTHODE ET LIMITES — présentes, prouvables, et repliées.
 *
 * CE QU'ELLE REMPLACE. Quatre pages posaient sous leur module dominant deux
 * paragraphes permanents : la méthode de calcul avec sa lignée, puis les
 * limites. Mesuré sur Marchés : 470 caractères de prose grise sous une carte
 * qui porte déjà sa figure, sa légende, sa provenance et son équivalent
 * tabulaire. Un lecteur qui lit tout ne lit plus rien.
 *
 * POURQUOI ON NE LES SUPPRIME PAS. Une limite tue est pire qu'une limite
 * illisible : « breadth refusée sous le seuil de couverture » est exactement
 * ce qui empêche de lire un chiffre partiel comme un chiffre complet. La
 * méthode porte la lignée — moteur, hash d'entrée, licence du rendu — et c'est
 * la traçabilité exigée par `financial-safety.md`.
 *
 * CE QUE LA DIVULGATION CHANGE, ET CE QU'ELLE NE CHANGE PAS. Le texte reste
 * dans le document : atteignable au clavier, lu par les technologies
 * d'assistance, trouvé par la recherche du navigateur, présent dans une
 * impression. Ce n'est pas une suppression, c'est un pli.
 *
 * CE QUI NE SE REPLIE JAMAIS. Rien de ce qui rend un chiffre lisible ne passe
 * ici : ni l'unité, ni la période, ni le fuseau, ni la source, ni la
 * fraîcheur, ni l'état de la donnée, ni le motif d'une absence. Ceux-là
 * restent en surface, sur la figure elle-même — `frontend.md` l'exige, et un
 * chiffre sans son unité n'est pas une information repliée, c'est une
 * information fausse.
 */
export interface MethodNoteProps {
  /** Comment la valeur a été produite : moteur, lignée, licence de rendu. */
  readonly methode: ReactNode;
  /**
   * Ce que la valeur ne dit PAS. Obligatoire : un module sans limite déclarée
   * est un module dont on n'a pas cherché les limites.
   */
  readonly limites: ReactNode;
  /**
   * Attribution de licence du moteur de rendu — TOUJOURS VISIBLE.
   *
   * Elle ne peut pas se replier. Apache-2.0 exige que la mention accompagne
   * l'œuvre ; une attribution derrière un bouton n'accompagne rien, elle
   * attend. Un test e2e le gèle déjà pour Lightweight Charts, et il avait
   * raison : la première version de ce composant l'avait repliée avec le
   * reste, et c'est ce test qui l'a rattrapée.
   */
  readonly attribution?: ReactNode;
  /** Accroche de test sur le paragraphe de limites, quand une assertion le vise. */
  readonly limitesTestId?: string;
}

export function MethodNote({ methode, limites, attribution, limitesTestId }: MethodNoteProps) {
  return (
    <footer className="vx-chartframe-foot">
      {attribution === undefined ? null : (
        <p className="vx-method-note-attribution">{attribution}</p>
      )}
      <details className="vx-method-note">
        <summary>Méthode et limites</summary>
        <div className="vx-method-note-body">
          <p>
            <span className="vx-method-note-tag">Méthode</span> {methode}
          </p>
          <p {...(limitesTestId === undefined ? {} : { 'data-testid': limitesTestId })}>
            <span className="vx-method-note-tag">Limites</span> {limites}
          </p>
        </div>
      </details>
    </footer>
  );
}
