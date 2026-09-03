import type { BarsView } from './analysisView.ts';

/** Table OHLCV ÉQUIVALENTE aux chandeliers : mêmes chaînes serveur, verbatim. */
export function OhlcvTable({ bars, currency }: { readonly bars: BarsView; readonly currency: string }) {
  return (
    <div
      className="vx-ohlcv-scroll"
      tabIndex={0}
      role="region"
      aria-label="Table OHLCV défilante"
    >
      <table className="vx-ohlcv-table" aria-label="Table OHLCV équivalente des chandeliers">
        <thead>
          <tr>
            <th scope="col">Jour</th>
            <th scope="col">Open ({currency})</th>
            <th scope="col">High ({currency})</th>
            <th scope="col">Low ({currency})</th>
            <th scope="col">Close ({currency})</th>
            <th scope="col">Volume</th>
          </tr>
        </thead>
        <tbody>
          {bars.bars.map((bar) => (
            <tr key={bar.tradingDay}>
              <th scope="row">
                <time dateTime={bar.tradingDay}>{bar.tradingDay}</time>
              </th>
              <td className="vx-num">{bar.open}</td>
              <td className="vx-num">{bar.high}</td>
              <td className="vx-num">{bar.low}</td>
              <td className="vx-num">{bar.close}</td>
              <td className="vx-num">{bar.volume}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

