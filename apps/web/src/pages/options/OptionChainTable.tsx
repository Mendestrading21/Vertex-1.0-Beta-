import { Fragment, useCallback, useId, useMemo, useState } from 'react';

import type { OptionChainContract, OptionChainExpiration } from '../../api/client.ts';
import { AbsentCell } from '../../components/absence.tsx';
import {
  CHAIN_COLUMNS,
  CHAIN_COLUMNS_DEFAULT,
  CHAIN_COLUMNS_MAX,
  COLONNES_NON_SERVIES,
  columnByKey,
} from './chainColumns.ts';
import type { ChainColumn } from './chainColumns.ts';
import { buildStrikeRows, geometryNumber, quoteViewOf } from './optionsView.ts';

/**
 * CHAÎNE D'OPTIONS — CALLS | STRIKE | PUTS.
 *
 * DÉCISION DE RENDU, MESURÉE. Le worker publie au plus 240 lignes de contrat
 * toutes échéances confondues (`vertex_worker/options.py:184`) et TRONQUE
 * au-delà en publiant `truncated_rows` ; le générateur synthétique produit 12
 * strikes par échéance. La chaîne rend donc 12 lignes par groupe et ne peut
 * structurellement pas dépasser 120 lignes. Aucune virtualisation n'est
 * introduite : à ce volume elle ne gagne rien et coûte la sémantique de
 * `<table>` native — donc la lecture par lecteur d'écran, la recherche du
 * navigateur et la copie de la chaîne. Les lignes portent
 * `content-visibility: auto` comme fenêtrage CSS léger si un instantané
 * approchait du budget.
 *
 * CE QUI EST AFFICHÉ, ET CE QUI NE PEUT PAS L'ÊTRE. Douze colonnes SERVIES sont
 * disponibles par côté (`chainColumns.ts`), dont `bid_size`, `ask_size`,
 * `volume` et `open_interest`, qui voyageaient jusqu'ici sans jamais être
 * rendus. Le spread, le mid et le dernier échangé n'existent PAS dans le
 * contrat : les fabriquer serait un calcul financier dans le navigateur. La
 * chaîne le DIT sous son sélecteur, au lieu de laisser croire à un manque de
 * place.
 *
 * LE SPOT PLUTÔT QUE « ATM ». Aucun champ ne classe un strike à la monnaie, et
 * ce rangement est un jugement qui appartient au moteur. La table insère donc
 * une ligne de REPÈRE portant le spot SERVI, à sa position dans l'échelle des
 * strikes. C'est une valeur publiée placée sur un axe publié — pas une
 * catégorie inventée.
 *
 * PROVENANCE PAR CELLULE. Chaque valeur porte son statut publié : une cotation
 * non `OK` affiche son statut en toutes lettres à côté du nombre, une absence
 * porte sa raison typée dans son nom accessible. Jamais un zéro à la place
 * d'une absence.
 */

export interface OptionChainTableProps {
  readonly group: OptionChainExpiration;
  readonly onInspect: (contract: OptionChainContract) => void;
  /** Contrat sélectionné, pour que la ligne se distingue. */
  readonly selectedConId?: number | null;
  /** Spot SERVI, verbatim, pour le repère. `null` = aucun repère tracé. */
  readonly spotValue?: string | null;
  readonly spotObservedAt?: string | null;
}

/**
 * Une cellule de valeur servie, avec son statut de cotation quand il n'est pas `OK`.
 *
 * LA CELLULE NE PORTE PAS `vx-num` — ET C'EST UN CORRECTIF, PAS UN OUBLI.
 *
 * Le `<td>` portait cette classe pour hériter du chiffre tabulaire. Quand
 * `.vx-num` a reçu `display: inline-block` — nécessaire pour que le plafond de
 * largeur agisse enfin sur le `<code>`, qui est inline — la classe a retiré aux
 * cellules leur `display: table-cell`. Un `<td>` qui n'est plus une cellule est
 * enveloppé par le navigateur dans des boîtes de tableau ANONYMES : mesuré, les
 * quatre valeurs d'un côté se retrouvaient dans une seule colonne, et l'en-tête
 * ne tombait plus en face du corps. La classe reste sur la VALEUR, jamais sur
 * son contenant ; `data-col` identifie la cellule.
 */
function ValueCell({
  contract,
  column,
}: {
  readonly contract: OptionChainContract;
  readonly column: ChainColumn;
}) {
  const valeur = column.read(contract);
  if (valeur === null) {
    const raison = column.absentReason?.(contract) ?? null;
    // Le code serveur reste VERBATIM — c'est lui qui fait foi — et la phrase
    // française l'accompagne quand le vocabulaire du worker la définit. Les
    // deux, jamais l'un à la place de l'autre.
    const explique = column.explain?.(raison);
    return (
      <AbsentCell
        quoi={column.label.toLowerCase()}
        nature={column.group === 'sensibilité' ? 'not_computed' : 'not_published'}
        reason={raison}
        {...(explique === undefined ? {} : { explained: explique })}
        {...(column.key === 'iv' ? { accord: 'f' as const } : {})}
      />
    );
  }
  const quote = quoteViewOf(contract);
  const statutCotation = column.group === 'cotation' || column.group === 'liquidité' ? quote.status : null;
  const provenance = `${column.label} : ${valeur} — ${column.definition}${
    quote.observedAt === null ? '' : ` Observé ${quote.observedAt}.`
  }`;
  return (
    <span title={provenance}>
      <code className="vx-num">{valeur}</code>
      {/* Le statut DOUBLE l'information par du texte : jamais une couleur seule. */}
      {statutCotation !== null && statutCotation !== 'OK' ? (
        <span className="vx-quote-status" data-status={statutCotation}>
          {statutCotation}
        </span>
      ) : null}
    </span>
  );
}

function SideCells({
  contract,
  side,
  columns,
  onInspect,
}: {
  readonly contract: OptionChainContract | null;
  readonly side: 'CALL' | 'PUT';
  readonly columns: readonly ChainColumn[];
  readonly onInspect: (contract: OptionChainContract) => void;
}) {
  if (contract === null) {
    const absent = <AbsentCell quoi={`contrat ${side} à ce strike`} nature="not_published" reason={null} />;
    return (
      <>
        {columns.map((colonne) => (
          <td key={colonne.key} data-col={colonne.key} data-side={side}>
            {absent}
          </td>
        ))}
        <td />
      </>
    );
  }
  return (
    <>
      {/* `data-col` et `data-side` rendent chaque cellule ADRESSABLE par ce
          qu'elle contient, pas par sa position. Avec des colonnes
          configurables, un index de cellule ne désigne plus rien de stable :
          l'e2e visait `nth(5)` et se cassait dès qu'on changeait la sélection
          par défaut. */}
      {columns.map((colonne) => (
        <td key={colonne.key} data-col={colonne.key} data-side={side}>
          <ValueCell contract={contract} column={colonne} />
        </td>
      ))}
      <td className="vx-chain-inspect-cell">
        <button
          type="button"
          className="vx-chain-inspect"
          aria-haspopup="dialog"
          onClick={() => {
            onInspect(contract);
          }}
          aria-label={`Inspecter ${side} strike ${contract.strike ?? 'non publié'} ${contract.expiration} ${contract.trading_class}`}
        >
          Détail
        </button>
      </td>
    </>
  );
}

/**
 * Sélecteur de colonnes — un `fieldset` de cases, pas un menu déroulant.
 *
 * Un menu cacherait l'état courant derrière un clic ; ici l'utilisateur voit
 * d'un coup d'œil ce qui est affiché et ce qui est disponible. Le plafond
 * empêche de dépasser sept colonnes par côté : au-delà, la comparaison d'un
 * strike à l'autre — l'objet même de la chaîne — devient impossible.
 */
function ColumnPicker({
  selection,
  onToggle,
  id,
}: {
  readonly selection: readonly string[];
  readonly onToggle: (key: string) => void;
  readonly id: string;
}) {
  const groupes: ReadonlyArray<ChainColumn['group']> = ['cotation', 'liquidité', 'sensibilité'];
  const plein = selection.length >= CHAIN_COLUMNS_MAX;
  return (
    <details className="vx-chain-columns">
      <summary>
        Colonnes affichées : {selection.length} sur {CHAIN_COLUMNS.length} servies
      </summary>
      <div className="vx-chain-columns-body">
        {groupes.map((groupe) => (
          <fieldset className="vx-chain-columns-group" key={groupe}>
            <legend>{groupe}</legend>
            {CHAIN_COLUMNS.filter((colonne) => colonne.group === groupe).map((colonne) => {
              const cochee = selection.includes(colonne.key);
              return (
                <label className="vx-chain-column-option" key={colonne.key} title={colonne.definition}>
                  <input
                    type="checkbox"
                    checked={cochee}
                    // Le plafond bloque l'AJOUT, jamais le retrait : on ne
                    // piège pas l'utilisateur dans une sélection saturée.
                    disabled={!cochee && plein}
                    onChange={() => {
                      onToggle(colonne.key);
                    }}
                  />
                  <span>{colonne.label}</span>
                  <span className="vx-chain-column-unit">{colonne.unit}</span>
                </label>
              );
            })}
          </fieldset>
        ))}
        {plein ? (
          <p className="vx-chain-columns-cap" role="status">
            Sept colonnes par côté au maximum : au-delà, comparer deux strikes devient illisible.
            Retirez-en une pour en ajouter une autre.
          </p>
        ) : null}
        {/*
          Dire ce qui n'existe PAS est aussi important que montrer ce qui existe :
          sans cette liste, chercher le spread laisse croire à un oubli
          d'interface, alors que le champ n'est pas publié et que le fabriquer
          serait un calcul interdit.
        */}
        <div className="vx-chain-columns-absent">
          <p className="vx-chain-columns-absent-title">Non publiées par le contrat</p>
          <dl id={id}>
            {COLONNES_NON_SERVIES.map((entree) => (
              <div key={entree.nom}>
                <dt>{entree.nom}</dt>
                <dd>{entree.motif}</dd>
              </div>
            ))}
          </dl>
        </div>
      </div>
    </details>
  );
}

export function OptionChainTable({
  group,
  onInspect,
  selectedConId = null,
  spotValue = null,
  spotObservedAt = null,
}: OptionChainTableProps) {
  const [selection, setSelection] = useState<readonly string[]>(CHAIN_COLUMNS_DEFAULT);
  const absentId = useId();

  const basculer = useCallback((key: string) => {
    setSelection((precedent) => {
      if (precedent.includes(key)) {
        // On ne descend jamais sous une colonne : une chaîne sans aucune valeur
        // n'est plus une chaîne.
        return precedent.length === 1 ? precedent : precedent.filter((k) => k !== key);
      }
      return precedent.length >= CHAIN_COLUMNS_MAX ? precedent : [...precedent, key];
    });
  }, []);

  // L'ordre des colonnes suit le vocabulaire, jamais l'ordre de cochage : la
  // chaîne doit avoir la même forme d'une session à l'autre.
  const colonnes = useMemo(
    () => CHAIN_COLUMNS.filter((colonne) => selection.includes(colonne.key)),
    [selection],
  );

  const { rows, unpairable } = buildStrikeRows(group);

  /**
   * Position du repère de spot : l'index de la PREMIÈRE ligne dont le strike
   * dépasse le spot servi.
   *
   * C'est un classement sur une échelle publiée, pas un calcul financier :
   * aucune valeur nouvelle n'est produite, on place un nombre servi entre deux
   * nombres servis. Si le spot n'est pas publié ou illisible, aucun repère
   * n'est tracé — plutôt qu'un repère placé au hasard.
   */
  const indexSpot = useMemo(() => {
    if (spotValue === null) {
      return null;
    }
    const spot = geometryNumber(spotValue);
    if (!Number.isFinite(spot)) {
      return null;
    }
    const index = rows.findIndex((ligne) => geometryNumber(ligne.strike) > spot);
    return index === -1 ? rows.length : index;
  }, [rows, spotValue]);

  const largeurTotale = colonnes.length * 2 + 3;

  return (
    <div className="vx-chain">
      <ColumnPicker selection={selection} onToggle={basculer} id={absentId} />
      {/* Région défilante focalisable au clavier (exigence axe) : le contenu
          large défile dans SON conteneur, jamais la page. */}
      <div
        className="vx-chain-table-scroll"
        tabIndex={0}
        role="region"
        aria-label={`Chaîne défilante ${group.expiration} ${group.trading_class}`}
      >
        <table
          className="vx-chain-table"
          aria-label={`Chaîne d'options ${group.expiration} ${group.trading_class}`}
        >
          <caption className="vx-chain-caption">
            Chaîne {group.trading_class} — échéance {group.expiration}
            <span className="vx-chain-caption-detail">
              {rows.length} strikes servis · {colonnes.length} colonnes affichées sur{' '}
              {CHAIN_COLUMNS.length} servies · valeurs verbatim, aucun calcul local
            </span>
          </caption>
          <thead>
            <tr>
              <th colSpan={colonnes.length + 1} scope="colgroup" className="vx-chain-side-head">
                Calls
              </th>
              <th rowSpan={2} scope="col" className="vx-chain-strike-head">
                Strike
                <span className="vx-chain-head-unit">{group.currency}</span>
              </th>
              <th colSpan={colonnes.length + 1} scope="colgroup" className="vx-chain-side-head">
                Puts
              </th>
            </tr>
            <tr>
              {colonnes.map((colonne) => (
                <th scope="col" key={`call-${colonne.key}`} title={colonne.definition}>
                  {colonne.label}
                  <span className="vx-chain-head-unit">{colonne.unit}</span>
                </th>
              ))}
              <th scope="col">
                <span className="vx-visually-hidden">Inspecter (call)</span>
              </th>
              {colonnes.map((colonne) => (
                <th scope="col" key={`put-${colonne.key}`} title={colonne.definition}>
                  {colonne.label}
                  <span className="vx-chain-head-unit">{colonne.unit}</span>
                </th>
              ))}
              <th scope="col">
                <span className="vx-visually-hidden">Inspecter (put)</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => {
              const selectionnee =
                selectedConId !== null &&
                (row.call?.con_id === selectedConId || row.put?.con_id === selectedConId);
              return (
                /*
                  `Fragment` NOMMÉ et porteur de la clé : le raccourci `<>` ne
                  peut pas en porter, et React perdrait alors la réconciliation
                  de la liste — la ligne de repère du spot et les lignes de
                  strike se mélangeraient au moindre changement d'échéance.
                */
                <Fragment key={row.strike}>
                  {indexSpot === index ? (
                    <tr className="vx-chain-spot">
                      <td colSpan={largeurTotale}>
                        {/* Une valeur PUBLIÉE, placée sur un axe publié. On ne
                            dit pas quel strike est « à la monnaie » : ce
                            rangement est un jugement du moteur.

                            UN SEUL élément collant, qui contient les autres.
                            Rendre chaque morceau collant les empilait tous au
                            MÊME décalage gauche : mesuré à l'écran, le libellé
                            et le nombre se chevauchaient — « spot servi366.08 ». */}
                        <span className="vx-chain-spot-inner">
                          <span className="vx-chain-spot-label">spot servi</span>
                          <code className="vx-num">{spotValue}</code>
                          <span className="vx-chain-spot-unit">{group.currency}</span>
                          {spotObservedAt === null ? (
                            <span className="vx-chain-spot-when">instant d’observation non publié</span>
                          ) : (
                            <time className="vx-chain-spot-when" dateTime={spotObservedAt}>
                              observé {spotObservedAt}
                            </time>
                          )}
                        </span>
                      </td>
                    </tr>
                  ) : null}
                  {/* `data-row` distingue une ligne de STRIKE du repère de
                      spot : sans cette accroche, compter « toutes les lignes du
                      tbody » mélange les deux, et une assertion qui vise les
                      strikes se casse dès qu'on ajoute un repère. */}
                  <tr
                    data-row="strike"
                    {...(selectionnee ? { 'data-selected': 'true', 'aria-current': 'true' as const } : {})}
                  >
                    <SideCells contract={row.call} side="CALL" columns={colonnes} onInspect={onInspect} />
                    <th scope="row" className="vx-chain-strike">
                      <code className="vx-num">{row.strike}</code>
                    </th>
                    <SideCells contract={row.put} side="PUT" columns={colonnes} onInspect={onInspect} />
                  </tr>
                </Fragment>
              );
            })}
            {indexSpot === rows.length ? (
              <tr className="vx-chain-spot">
                <td colSpan={largeurTotale}>
                  <span className="vx-chain-spot-inner">
                    <span className="vx-chain-spot-label">spot servi</span>
                    <code className="vx-num">{spotValue}</code>
                    <span className="vx-chain-spot-unit">{group.currency}</span>
                    <span className="vx-chain-spot-when">au-dessus de tous les strikes servis</span>
                  </span>
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
      {unpairable.length > 0 ? (
        <p className="vx-chain-unpairable" role="status">
          {unpairable.length} contrat(s) à identité incomplète publiés hors table (strike ou right
          illisible) — aucun calcul n'existe pour eux, voir la couverture du groupe.
        </p>
      ) : null}
    </div>
  );
}

export { columnByKey };
