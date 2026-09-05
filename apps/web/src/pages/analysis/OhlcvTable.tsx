import { DataTable } from '../../components/widgets/DataTable.tsx';
import type { DataColumn } from '../../components/widgets/DataTable.tsx';
import type { BarsView } from './analysisView.ts';

/**
 * Table OHLCV ÉQUIVALENTE aux chandeliers : mêmes chaînes serveur, verbatim.
 *
 * PREMIER CONSOMMATEUR DE `DataTable`. Ce que la migration change réellement,
 * au-delà d'une classe CSS de moins :
 *
 *   - la table portait un `aria-label` et AUCUN `<caption>` — elle faisait
 *     partie des 18 tables dont le nom était invisible à l'écran et absent des
 *     captures. Elle a maintenant une légende lisible par tout le monde ;
 *   - l'ordre des barres n'était pas déclaré. Il vient du serveur, du plus
 *     ancien au plus récent ; la légende le DIT désormais, au lieu de laisser
 *     croire qu'un tri d'affichage a été appliqué ;
 *   - une série vide rendait une table à zéro ligne, c'est-à-dire un en-tête
 *     seul et rien en dessous. Elle se NOMME maintenant ;
 *   - l'unité vit dans l'en-tête sous le nom de colonne, en clair, au lieu
 *     d'être collée au titre entre parenthèses.
 */

type Bar = BarsView['bars'][number];

function colonnes(currency: string): ReadonlyArray<DataColumn<Bar>> {
  return [
    {
      key: 'day',
      header: 'Jour',
      align: 'text',
      rowHeader: true,
      width: 'ch12',
      cell: (bar) => <time dateTime={bar.tradingDay}>{bar.tradingDay}</time>,
    },
    { key: 'open', header: 'Open', align: 'num', unit: currency, cell: (bar) => bar.open },
    { key: 'high', header: 'High', align: 'num', unit: currency, cell: (bar) => bar.high },
    { key: 'low', header: 'Low', align: 'num', unit: currency, cell: (bar) => bar.low },
    { key: 'close', header: 'Close', align: 'num', unit: currency, cell: (bar) => bar.close },
    // Le volume n'est pas en devise : son unité est le contrat/titre échangé.
    // Réutiliser `currency` ici aurait été une unité fausse.
    { key: 'volume', header: 'Volume', align: 'num', unit: 'titres', cell: (bar) => bar.volume },
  ];
}

export function OhlcvTable({ bars, currency }: { readonly bars: BarsView; readonly currency: string }) {
  return (
    <DataTable<Bar>
      id="vx-ohlcv"
      caption="Table OHLCV — équivalent exact des chandeliers"
      captionDetail={`valeurs serveur verbatim, ${currency}, une ligne par séance`}
      columns={colonnes(currency)}
      rows={bars.bars}
      rowKey={(bar) => bar.tradingDay}
      density="dense"
      overflow="panel"
      emptyLabel="aucune séance publiée pour cette période"
      // L'ordre est celui du serveur : la plus ancienne séance d'abord. On le
      // déclare, on ne le refait pas.
      servedOrder={{ by: 'day', direction: 'asc' }}
    />
  );
}
