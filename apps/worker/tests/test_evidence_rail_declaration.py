"""Ce que CHAQUE consommateur déclare doit exister dans le semis — et l'inverse.

CE TEST EXISTE À CAUSE D'UNE RÉGRESSION MESURÉE (CI GitHub, exécution
33750177958) : le rail de preuves déclarait les seules familles de dépêches
alors que, dans la population de démonstration, aucune dépêche ne parle des
tickers de l'univers. Le rail rendait 0 grappe, l'explication IA 0 extrait
externe, et rien n'échouait côté serveur.

Une déclaration se trompe de deux façons, et les DEUX sont refusées ici :

1. le consommateur ne déclare pas une famille que le semis produit ET dont il
   a besoin (ici : le rail affamé, la régression ci-dessus) ;
2. le consommateur déclare une famille SYNTHÉTIQUE que le semis ne produit
   pas — une déclaration qui ne nomme rien, donc une couverture publiée qui
   ment sur ce qui a été regardé.

Le semis est lu à sa source (`vertex_worker.demo_seed` et les générateurs de
`vertex_core.synthetic`), jamais recopié : ce test suit le semis, il ne le
fige pas. Aucune base n'est nécessaire — ce sont les enveloppes, avant
ingestion.
"""

from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Any

from vertex_core.synthetic import (
    SYNTHETIC_FOCUS_TICKERS,
    generate_calendar_event_envelopes,
    generate_daily_bar_envelopes,
    generate_daily_quote_envelopes,
    generate_envelopes,
    generate_option_chain_envelopes,
)
from vertex_worker.calendar import CALENDAR_EVENT_SCHEMA_PREFIXES
from vertex_worker.demo_seed import ENVELOPE_COUNT, SEED
from vertex_worker.handlers import CONTENT_SCHEMA_PREFIXES, EVIDENCE_SCHEMA_PREFIXES

BASE_TIME = datetime(2026, 9, 3, 10, 0, 0, tzinfo=UTC) - timedelta(minutes=5)

#: Le ticker que l'inspecteur IA explique dans le parcours e2e
#: (`apps/web/e2e/ai-inspector.spec.ts`).
INSTRUMENT_EXPLIQUE = "SYN-TECH-01"


def _enveloppes_du_semis() -> tuple[Any, ...]:
    """Exactement ce que `seed_demo_population` écrit, à sa source."""
    return (
        *generate_envelopes(seed=SEED, count=ENVELOPE_COUNT, base_time=BASE_TIME),
        *generate_daily_quote_envelopes(seed=SEED, base_time=BASE_TIME),
        *generate_option_chain_envelopes(seed=SEED, base_time=BASE_TIME),
        *generate_daily_bar_envelopes(seed=SEED, base_time=BASE_TIME),
        *generate_calendar_event_envelopes(seed=SEED, base_time=BASE_TIME),
    )


def _porte_un_titre(enveloppe: Any) -> bool:
    charge = enveloppe.payload if isinstance(enveloppe.payload, Mapping) else {}
    titre = charge.get("title")
    return isinstance(titre, str) and bool(titre.strip())


def _familles(enveloppes: tuple[Any, ...]) -> set[str]:
    return {enveloppe.schema_version for enveloppe in enveloppes}


def _familles_titrees() -> set[str]:
    return _familles(tuple(e for e in _enveloppes_du_semis() if _porte_un_titre(e)))


def _declarees(famille: str, prefixes: tuple[str, ...]) -> bool:
    return famille.startswith(prefixes)


def test_le_rail_declare_toutes_les_familles_titrees_du_semis() -> None:
    """Sens 1 : une famille titrée que le rail ignore, c'est un rail affamé.

    Avant le correctif, `synthetic-calendar-event/1.0` n'était déclarée par
    aucun consommateur du rail : les dossiers de l'univers n'avaient plus
    aucune preuve.
    """
    titrees = _familles_titrees()
    assert titrees, "le semis ne produit plus aucune observation titrée"
    non_declarees = sorted(
        famille
        for famille in titrees
        if not _declarees(famille, EVIDENCE_SCHEMA_PREFIXES)
    )
    assert not non_declarees, (
        "familles titrées produites par le semis et absentes de la "
        f"déclaration du rail de preuves : {non_declarees}"
    )


def test_chaque_famille_synthetique_declaree_existe_dans_le_semis() -> None:
    """Sens 2 : une déclaration synthétique qui ne nomme rien est refusée.

    Les familles réelles (`ibkr.…`) ne sont pas concernées : le semis de
    démonstration n'en produit aucune, par construction.
    """
    presentes = _familles(_enveloppes_du_semis())
    for etiquette, prefixes in (
        ("file d'attention / revue", CONTENT_SCHEMA_PREFIXES),
        ("rail de preuves", EVIDENCE_SCHEMA_PREFIXES),
    ):
        orphelines = sorted(
            prefixe
            for prefixe in prefixes
            if prefixe.startswith("synthetic-")
            and not any(famille.startswith(prefixe) for famille in presentes)
        )
        assert not orphelines, (
            f"{etiquette} : préfixes synthétiques déclarés que le semis ne "
            f"produit pas : {orphelines}"
        )


def test_le_rail_ne_declare_aucune_famille_sans_titre() -> None:
    """Une famille sans titre ne produirait aucune grappe et rouvrirait la
    famine : les cotations instantanées chassent les preuves de la fenêtre
    bornée avant qu'elle ne soit lue (mesuré le 2026-09-03, 08:40 UTC)."""
    titrees = _familles_titrees()
    for famille in _familles(_enveloppes_du_semis()):
        if famille in titrees:
            continue
        assert not _declarees(famille, EVIDENCE_SCHEMA_PREFIXES), famille
        assert not _declarees(famille, CONTENT_SCHEMA_PREFIXES), famille


def test_l_instrument_explique_par_l_inspecteur_porte_une_preuve_declaree() -> None:
    """Le reproducteur de la régression, au niveau de la DÉCLARATION.

    `e2e/ai-inspector.spec.ts:89` exige au moins un extrait externe pour
    `SYN-TECH-01`, et un extrait externe n'a qu'une source : le titre d'une
    grappe du rail. Il faut donc, pour CE ticker, au moins une observation
    titrée d'une famille déclarée par le rail.
    """
    assert INSTRUMENT_EXPLIQUE in SYNTHETIC_FOCUS_TICKERS
    preuves = [
        enveloppe
        for enveloppe in _enveloppes_du_semis()
        if _porte_un_titre(enveloppe)
        and enveloppe.instrument_id == INSTRUMENT_EXPLIQUE
        and _declarees(enveloppe.schema_version, EVIDENCE_SCHEMA_PREFIXES)
    ]
    assert preuves, (
        f"aucune observation titrée et déclarée pour {INSTRUMENT_EXPLIQUE} : "
        "le rail de preuves de ce ticker est vide, donc l'explication IA ne "
        "peut porter aucun extrait externe"
    )


def test_le_partage_entre_la_file_et_le_rail_est_declare() -> None:
    """TÉMOIN du partage : le rail lit UNE famille de plus que la file, nommée.

    Un événement de calendrier porte un titre mais n'est pas une dépêche : la
    file d'attention et le contexte d'information de la revue ne le lisent
    pas ; le rail de preuves d'un instrument le cite. Le réintroduire dans la
    file — ou l'ôter du rail — est une décision de produit qui passe par ces
    deux listes, jamais par une borne plus large.
    """
    assert set(CONTENT_SCHEMA_PREFIXES) < set(EVIDENCE_SCHEMA_PREFIXES)
    assert set(EVIDENCE_SCHEMA_PREFIXES) - set(CONTENT_SCHEMA_PREFIXES) == set(
        CALENDAR_EVENT_SCHEMA_PREFIXES
    )
    for famille in (*CALENDAR_EVENT_SCHEMA_PREFIXES, "synthetic-calendar-event/1.0"):
        assert not famille.startswith(CONTENT_SCHEMA_PREFIXES), famille
        assert famille.startswith(EVIDENCE_SCHEMA_PREFIXES), famille
