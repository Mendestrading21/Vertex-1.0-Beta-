import type { OptionChainContract, OptionChainExpiration } from '../../api/client.ts';
import { AbsentCell } from '../../components/absence.tsx';
import { IV_ABSENT_REASONS_FR, buildStrikeRows, deltaOf, ivViewOf, quoteViewOf } from './optionsView.ts';

/**
 * Table de chaîne Calls | Strike | Puts — dominante de la page Options.
 *
 * DÉCISION DE RENDU (documentée, aucune dépendance nouvelle) : le serveur
 * publie ~24 contrats par groupe (12 strikes x CALL/PUT), soit 12 lignes de
 * table, et borne lui-même la chaîne par `row_budget` (240 lignes max toutes
 * expirations). Sous 200 lignes, le rendu DIRECT est plus simple et plus
 * accessible qu'une virtualisation ; les lignes portent
 * `content-visibility: auto` (voir .vx-chain-table tbody tr) comme fenêtrage
 * CSS léger si un futur snapshot approche du budget. Aucune bibliothèque de
 * virtualisation n'est introduite.
 *
 * Provenance PAR CELLULE : chaque valeur porte son statut publié —
 * bid/ask affichent le statut de quote quand il n'est pas `OK` (texte, pas
 * seulement une couleur) et l'horodatage observé au survol ; une IV absente
 * est rendue « — » avec la raison typée au survol (title) et en accessible
 * name — JAMAIS un zéro. Le détail complet vit dans l'inspecteur.
 */

export interface OptionChainTableProps {
  readonly group: OptionChainExpiration;
  readonly onInspect: (contract: OptionChainContract) => void;
}

function QuoteCell({
  value,
  status,
  observedAt,
  side,
}: {
  readonly value: string | null;
  readonly status: string | null;
  readonly observedAt: string | null;
  readonly side: string;
}) {
  if (value === null) {
    // Le statut de quote SERVI est le motif : « bid non publié (CROSSED) ».
    return <AbsentCell quoi={side} nature="not_published" reason={status} />;
  }
  const provenance = `${side} verbatim — statut de quote ${status ?? 'inconnu'}, observé ${
    observedAt ?? 'à un instant non publié'
  }`;
  return (
    <span title={provenance}>
      <code className="vx-num">{value}</code>
      {status !== null && status !== 'OK' ? (
        <span className="vx-quote-status" data-status={status}>
          {status}
        </span>
      ) : null}
    </span>
  );
}

function IvCell({ contract }: { readonly contract: OptionChainContract }) {
  const iv = ivViewOf(contract);
  if (iv.status !== 'OK' || iv.value === null) {
    // L'IV n'est pas « absente » : le moteur a REFUSÉ de la calculer, avec sa
    // raison typée. `not_computed` dit lequel des deux, et le code serveur
    // reste verbatim dans le nom accessible — deux assertions le cherchent.
    return (
      <AbsentCell
        quoi="IV"
        nature="not_computed"
        reason={iv.reason}
        {...(iv.reason === null ? {} : { explained: IV_ABSENT_REASONS_FR[iv.reason] })}
        accord="f"
      />
    );
  }
  // La chaîne EXACTE est dans le `title` avec sa provenance : rien n'est perdu.
  // Le rendu, lui, est borné par la colonne (voir `.vx-chain-table .vx-num` dans
  // `global.css`) — une IV sur 16 décimales détruit l'alignement de la colonne,
  // et une colonne désalignée est une chaîne d'options qu'on ne peut pas
  // comparer d'un strike à l'autre. La valeur n'est PAS arrondie : arrondir
  // fabriquerait un nombre que le worker n'a pas publié.
  const provenance = `${iv.value} — IV Vertex THÉORIQUE (côté ${iv.quoteSide ?? 'non publié'}) — ${
    iv.calculation?.calculationId ?? 'lignée non publiée'
  }`;
  return (
    <span title={provenance}>
      <code className="vx-num">{iv.value}</code>
    </span>
  );
}

function DeltaCell({ contract }: { readonly contract: OptionChainContract }) {
  const delta = deltaOf(contract);
  if (delta === null) {
    // Le delta n'est pas calculé PARCE QUE l'IV ne l'est pas : la cause est
    // servie, elle est donc dite.
    return (
      <AbsentCell
        quoi="delta"
        nature="not_computed"
        reason={ivViewOf(contract).reason}
        explained="IV non résolue, aucun Greek calculé"
      />
    );
  }
  // Même règle que l'IV : la chaîne exacte au survol, le rendu borné par la
  // colonne. Le delta n'est jamais arrondi ici.
  return (
    <span
      title={`${delta} — Delta Vertex THÉORIQUE (voir l’inspecteur pour la lignée complète)`}
    >
      <code className="vx-num">{delta}</code>
    </span>
  );
}

function SideCells({
  contract,
  side,
  onInspect,
}: {
  readonly contract: OptionChainContract | null;
  readonly side: 'CALL' | 'PUT';
  readonly onInspect: (contract: OptionChainContract) => void;
}) {
  if (contract === null) {
    const absent = <AbsentCell quoi={`contrat ${side} à ce strike`} nature="not_published" reason={null} />;
    return (
      <>
        <td className="vx-num">{absent}</td>
        <td className="vx-num">{absent}</td>
        <td className="vx-num">{absent}</td>
        <td className="vx-num">{absent}</td>
        <td />
      </>
    );
  }
  const quote = quoteViewOf(contract);
  return (
    <>
      <td className="vx-num">
        <QuoteCell value={quote.bid} status={quote.status} observedAt={quote.observedAt} side="bid" />
      </td>
      <td className="vx-num">
        <QuoteCell value={quote.ask} status={quote.status} observedAt={quote.observedAt} side="ask" />
      </td>
      <td className="vx-num">
        <IvCell contract={contract} />
      </td>
      <td className="vx-num">
        <DeltaCell contract={contract} />
      </td>
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

export function OptionChainTable({ group, onInspect }: OptionChainTableProps) {
  const { rows, unpairable } = buildStrikeRows(group);
  return (
    // Région défilante focalisable au clavier (exigence axe) : le contenu
    // large défile dans SON conteneur, jamais la page.
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
        <thead>
          <tr>
            <th colSpan={5} scope="colgroup" className="vx-chain-side-head">
              Calls
            </th>
            <th rowSpan={2} scope="col" className="vx-chain-strike-head">
              Strike ({group.currency})
            </th>
            <th colSpan={5} scope="colgroup" className="vx-chain-side-head">
              Puts
            </th>
          </tr>
          <tr>
            <th scope="col">Bid</th>
            <th scope="col">Ask</th>
            <th scope="col">IV</th>
            <th scope="col">Delta</th>
            <th scope="col">
              <span className="vx-visually-hidden">Inspecter (call)</span>
            </th>
            <th scope="col">Bid</th>
            <th scope="col">Ask</th>
            <th scope="col">IV</th>
            <th scope="col">Delta</th>
            <th scope="col">
              <span className="vx-visually-hidden">Inspecter (put)</span>
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.strike}>
              <SideCells contract={row.call} side="CALL" onInspect={onInspect} />
              <th scope="row" className="vx-chain-strike">
                <code className="vx-num">{row.strike}</code>
              </th>
              <SideCells contract={row.put} side="PUT" onInspect={onInspect} />
            </tr>
          ))}
        </tbody>
      </table>
      {unpairable.length > 0 ? (
        <p className="vx-chain-unpairable" role="status">
          {unpairable.length} contrat(s) à identité incomplète publiés hors table (strike ou right
          illisible) — aucun calcul n'existe pour eux, voir la couverture du groupe.
        </p>
      ) : null}
    </div>
  );
}
