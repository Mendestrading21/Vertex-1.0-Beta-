import { Link } from 'react-router-dom';

import { useCalendar } from '../../api/decisionApi.ts';
import { pageStateOf } from '../../api/hooks.ts';
import { AbsentModule } from '../../components/AbsentModule.tsx';
import { Card } from '../../components/Card.tsx';
import { ModuleStatus } from '../../components/ModuleStatus.tsx';
import { AgendaLine } from '../../components/calendar/AgendaLine.tsx';
import { moduleShowsContent, moduleStateOf } from '../../components/moduleState.ts';
import { calendarEventsOf } from '../calendar/calendarView.ts';
import { simulatorModule } from './simulatorModules.ts';
import type { SimulatorTransfer } from './transfer.ts';

/**
 * Les modules du Simulateur qui ne lisent pas le résultat : les catalyseurs
 * du sous-jacent transféré (agenda publié), la provenance des valeurs
 * préremplies, et les modules absents. Sans transfert, aucun sous-jacent
 * n'est connu : le module le DIT et n'ouvre aucune requête.
 */

const CATALYST_LINES = 6;

export function AbsentSimulatorModule({ id }: { readonly id: string }) {
  const module = simulatorModule(id);
  if (module.status.kind !== 'absent') {
    throw new Error(`Module ${id} is served, not absent`);
  }
  return (
    <div data-module={id}>
      <AbsentModule title={module.title} question={module.question} reason={module.status.reason} note={module.status.note} />
    </div>
  );
}

function CatalystsList({ underlying }: { readonly underlying: string }) {
  const query = useCalendar(null);
  const state = moduleStateOf(pageStateOf(query), query.data);
  const data = query.data;
  const events =
    data === undefined
      ? []
      : calendarEventsOf(Array.isArray(data.agenda) ? data.agenda : []).filter((event) => event.ticker === underlying);
  const lines = events.slice(0, CATALYST_LINES);
  return (
    <>
      <ModuleStatus state={state} raw={state === 'closed' ? data?.state : data?.reason} />
      {moduleShowsContent(state) && data !== undefined ? (
        lines.length === 0 ? (
          <p className="vx-module-sentence" role="status" data-testid="sim-catalysts-empty">
            Aucun événement publié pour <code>{underlying}</code> dans l’agenda.
          </p>
        ) : (
          <ul className="vx-agenda-mini" aria-label={`Événements publiés pour ${underlying}`} data-testid="sim-catalysts">
            {lines.map((event) => (
              <AgendaLine key={event.eventId} event={event} />
            ))}
          </ul>
        )
      ) : null}
    </>
  );
}

export function CatalystsModule({ transfer }: { readonly transfer: SimulatorTransfer | null }) {
  const module = simulatorModule('catalysts');
  return (
    <Card
      rank="quiet"
      kicker="Agenda publié"
      title={module.title}
      titleId="vx-sim-catalysts-title"
      footer={transfer === null ? <>aucune requête ouverte sans sous-jacent déclaré</> : <>sous-jacent du transfert · <Link to="/calendar">voir le calendrier</Link></>}
    >
      {transfer === null ? (
        <p className="vx-module-sentence" role="status">
          Aucun sous-jacent déclaré : une structure saisie à la main ne nomme aucun instrument, donc aucun catalyseur
          n’est cherché.
        </p>
      ) : (
        <CatalystsList underlying={transfer.underlying} />
      )}
    </Card>
  );
}

export function SourcesModule({ transfer }: { readonly transfer: SimulatorTransfer | null }) {
  const module = simulatorModule('sources');
  return (
    <Card rank="quiet" kicker="Provenance" title={module.title} titleId="vx-sim-sources-title" footer={<>l’état de navigation est perdu au rechargement : le composeur repart vide, jamais avec une intention périmée</>}>
      {transfer !== null ? (
        <p className="vx-sim-transfer" role="status" data-testid="sim-transfer-note">
          Préremplie depuis Options : {transfer.right} <code className="vx-num">{transfer.strike}</code> · {transfer.expiration} ·{' '}
          <code>{transfer.tradingClass}</code> (sous-jacent <code>{transfer.underlying}</code>
          {transfer.conId !== null ? (
            <>
              , con_id <code>{transfer.conId}</code>
            </>
          ) : null}
          ) — prime suggérée côté {transfer.premiumSide ?? 'non publié'}, spot et IV du snapshot ;
          tout reste éditable.{' '}
          {transfer.population === 'SYNTHETIC' ? <span className="vx-badge vx-badge-synthetic">SYNTHÉTIQUE</span> : null}
        </p>
      ) : (
        <p className="vx-module-sentence">Aucune valeur préremplie : structure et hypothèses saisies à la main.</p>
      )}
      <p className="vx-sim-scope" role="note">
        Étude théorique d'une structure DÉCLARÉE — tous les chiffres sont calculés par le serveur (<code>vertex_core</code>)
        et étiquetés THÉORIQUE ; rien ici n'est un prix exécutable ni une capacité de transaction. Sauvegarde :{' '}
        <code>NON_IMPLÉMENTÉ</code> — lot ultérieur.
      </p>
    </Card>
  );
}
