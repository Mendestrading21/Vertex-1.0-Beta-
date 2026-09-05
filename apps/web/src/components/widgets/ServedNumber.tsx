/**
 * UN NOMBRE SERVI — verbatim, borné au rendu, entier au survol.
 *
 * LE PROBLÈME, MESURÉ. Le moteur publie ses flottants ENTIERS. Sur Analyse :
 * ATR « 4.413571428571428 », MACD « 1.1490960023212681 », RSI
 * « 57.58443142661 ». Sur le simulateur : « -3731.5730453527934 ». Rendus tels
 * quels dans une carte de deux cents pixels, ils passent à la ligne au milieu
 * d'un chiffre, écrasent leur libellé, et la carte cesse d'être lisible — or
 * personne ne lit la seizième décimale d'un ATR à l'écran.
 *
 * CE QUE CE COMPOSANT NE FAIT PAS. Il n'ARRONDIT PAS. Arrondir fabriquerait un
 * nombre que le serveur n'a pas publié, et `financial-safety.md` l'interdit :
 * la chaîne servie est rendue telle quelle, seule sa LARGEUR est bornée. La
 * valeur complète reste dans le `title` — donc au survol et dans le nom
 * accessible — et une porte e2e vérifie que tout nombre rogné garde ce recours.
 *
 * POURQUOI `inline-block`. `max-width` et `text-overflow` ne s'appliquent pas à
 * un élément inline non remplacé : sur un `<code>` inline, le plafond est
 * INERTE. Mesuré une première fois sur la chaîne d'options — valeur rendue à
 * 149 px pour un plafond calculé à 86. C'est `inline-block` qui rend le
 * plafond effectif, et c'est aussi lui qui interdit de poser cette classe sur
 * une cellule de tableau : un `<td>` qui n'est plus `table-cell` cesse d'être
 * une cellule, et le navigateur enveloppe ses voisines dans des boîtes
 * anonymes. Ce composant rend donc un `<code>`, jamais un `<td>`.
 */
export interface ServedNumberProps {
  /** La chaîne SERVIE, verbatim. Jamais un nombre JavaScript : il arrondirait. */
  readonly value: string;
  /**
   * Largeur maximale de rendu, en caractères. Le défaut tient une cotation et
   * un pourcentage sans jamais les couper.
   */
  readonly maxChars?: number;
  readonly className?: string;
}

export function ServedNumber({ value, maxChars = 12, className }: ServedNumberProps) {
  return (
    <code
      className={className === undefined ? 'vx-served-number' : `vx-served-number ${className}`}
      style={{ maxWidth: `${maxChars}ch` }}
      // Le `title` porte TOUJOURS la valeur entière, même quand le rendu tient
      // dans le plafond : sans quoi le recours dépendrait de la largeur de la
      // fenêtre, donc de rien de fiable.
      title={value}
    >
      {value}
    </code>
  );
}
