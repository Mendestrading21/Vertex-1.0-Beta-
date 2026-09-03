import type { KeyboardEvent } from 'react';

/**
 * Fenêtres d'AFFICHAGE d'une série servie — un choix explicite de vue, jamais
 * un fenêtrage de calcul.
 *
 * L'arbitrage est consigné : `references/charts.md` réserve le fenêtrage au
 * serveur ; `docs/05-design/WIDGET_LIBRARY.md` autorise à « filtrer selon un
 * choix explicite de l'utilisateur ». Ce composant ne fait QUE la seconde
 * chose : il découpe l'affichage de barres DÉJÀ servies, et une fenêtre plus
 * large que la série publiée est DÉSACTIVÉE avec son motif visible — jamais
 * masquée, jamais complétée.
 */
export interface PeriodOption {
  readonly key: string;
  readonly label: string;
  readonly available: boolean;
  /** Motif SERVI de l'indisponibilité. Visible, jamais un silence. */
  readonly reason?: string;
}

export interface PeriodTabsProps {
  readonly options: readonly PeriodOption[];
  readonly value: string;
  readonly onChange: (key: string) => void;
  /** Légende disant qu'il s'agit d'un choix de VUE. */
  readonly legend: string;
}

export function PeriodTabs({ options, value, onChange, legend }: PeriodTabsProps) {
  // Aucune option publiée : le composant est absent, pas vide.
  if (options.length === 0) {
    return null;
  }

  const availables = options.filter((option) => option.available);

  function move(direction: 1 | -1): void {
    if (availables.length === 0) {
      return;
    }
    const current = availables.findIndex((option) => option.key === value);
    const base = current === -1 ? 0 : current;
    const next = (base + direction + availables.length) % availables.length;
    const target = availables[next];
    if (target !== undefined) {
      onChange(target.key);
    }
  }

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>): void {
    if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
      event.preventDefault();
      move(1);
    } else if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
      event.preventDefault();
      move(-1);
    }
  }

  const reasons = options.filter(
    (option) => !option.available && option.reason !== undefined && option.reason !== '',
  );

  return (
    <div className="vx-w2-periods-block">
      <div className="vx-w2-periods" role="group" aria-label={legend}>
        {options.map((option) => (
          <button
            key={option.key}
            type="button"
            className="vx-w2-period"
            aria-pressed={option.key === value}
            tabIndex={option.key === value ? 0 : -1}
            disabled={!option.available}
            onKeyDown={onKeyDown}
            onClick={() => {
              onChange(option.key);
            }}
          >
            {option.label}
          </button>
        ))}
      </div>
      <p className="vx-w2-period-reason">{legend}</p>
      {reasons.map((option) => (
        <p key={option.key} className="vx-w2-period-reason">
          {option.reason}
        </p>
      ))}
    </div>
  );
}
