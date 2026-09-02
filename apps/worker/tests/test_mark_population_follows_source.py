"""La nature des marques est CELLE DE LA SOURCE — jamais une constante.

POURQUOI CE FICHIER EXISTE. `docs/08-runbooks/REPRENDRE_ICI.md` §4.1 liste huit
etiquettes qui mentent sur la nature des donnees. Deux d'entre elles sont pires
que les six autres : elles ne mentent pas a l'ecran, elles mentent DANS LE
CONTENU PERSISTE.

`portfolio.py` ecrivait `mark_population = "SYNTHETIC"` INCONDITIONNELLEMENT,
avec ce commentaire : « Constant by design: the only marks Vertex 1.0 Beta has
are the synthetic last closes of the markets overview snapshot. » C'etait vrai
quand il a ete ecrit. Ce ne l'est plus : le poste de travail sert
`markets_overview` en `population = "REAL"` sur 161 instruments IBKR, dont
0 synthetique.

CE QUE CETTE CONSTANTE COUTE. Les tables `snapshots` sont APPEND-ONLY par
declencheur SQL : `UPDATE` et `DELETE` y sont refuses. Une valorisation publiee
avec une nature fausse n'est donc PAS rattrapable — elle reste telle quelle
jusqu'a ce qu'une republication la remplace. Une etiquette d'ecran se corrige
au prochain rendu ; celle-ci, non.

Et le sens du mensonge compte, meme s'il « rassure » : dire SYNTHETIQUE d'une
donnee reelle detruit la capacite du lecteur a savoir ce qu'il regarde, ce que
`.claude/rules/financial-safety.md` exige de preserver — « reel, retarde,
theorique, simule et demonstration ne partagent jamais le meme statut visuel ou
semantique ».

CE QUE LA CORRECTION N'EST PAS. Elle n'est pas « remplacer SYNTHETIC par
REAL » : ce serait deplacer le mensonge, pas le retirer. Sur cette machine tout
est vraiment synthetique. La nature doit etre RELAYEE depuis l'instantane
source, et rester fail-closed quand la source ne la declare pas.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from vertex_worker.portfolio import (
    LedgerEventView,
    PortfolioView,
    build_portfolio_valuation_content,
    extract_marks_from_markets_content,
)

NOW = datetime(2026, 9, 1, 12, 0, 0, tzinfo=UTC)

PORTEFEUILLE = PortfolioView(id=1, name="Registre declare", base_currency="USD")


def marches(population: Any, ticker: str = "SYN-A") -> dict[str, Any]:
    """Un instantane `markets_overview` minimal, nature imposee."""
    return {
        "as_of": "2026-09-01T00:00:00+00:00",
        "population": population,
        "sectors": [
            {
                "sector": "SYN",
                "label": "Secteur",
                "tickers": [
                    {
                        "ticker": ticker,
                        "last_close": "100.0000",
                        "currency": "USD",
                        "trading_day": "2026-08-31",
                    }
                ],
            }
        ],
    }


def achat(ticker: str = "SYN-A") -> LedgerEventView:
    """Un lot ouvert, declare par l'utilisateur — la seule origine admise."""
    return LedgerEventView(
        id=1,
        kind="BUY",
        instrument={"ticker": ticker},
        quantity=Decimal("10"),
        price=Decimal("90.0000"),
        amount=Decimal("-900.0000"),
        currency="USD",
        fees=Decimal("0"),
        effective_at=datetime(2026, 8, 1, 12, 0, 0, tzinfo=UTC),
        source="MANUAL",
        compensates=None,
    )


def valorisation(population: Any) -> dict[str, Any]:
    marks = extract_marks_from_markets_content(marches(population), snapshot_version=7)
    return build_portfolio_valuation_content(
        [achat()], portfolio=PORTEFEUILLE, marks=marks, now=NOW
    )


def test_une_source_reelle_donne_des_marques_reelles() -> None:
    """LE REPRODUCTEUR. Rouge tant que la constante est ecrite en dur.

    C'est le cas du poste de travail : `markets_overview` en `REAL`, et une
    valorisation qui se declarait `SYNTHETIC` par-dessus.
    """
    assert valorisation("REAL")["mark_population"] == "REAL"


def test_une_source_synthetique_donne_des_marques_synthetiques() -> None:
    """La moitie qui empeche de simplement inverser le mensonge.

    Sur une machine de developpement, la source EST synthetique. La correction
    doit relayer, pas remplacer une constante par une autre.
    """
    assert valorisation("SYNTHETIC")["mark_population"] == "SYNTHETIC"


def test_une_source_retardee_est_relayee_telle_quelle() -> None:
    """`DELAYED` n'est ni `REAL` ni `SYNTHETIC` — il ne doit se fondre dans ni l'un ni l'autre."""
    assert valorisation("DELAYED")["mark_population"] == "DELAYED"


def test_une_nature_absente_ne_valorise_RIEN() -> None:
    """FAIL-CLOSED : une marque non qualifiable ne vaut aucune position.

    Si la source ne declare pas sa nature, le lecteur ne peut pas savoir ce
    qu'il regarde. Publier quand meme, sous une etiquette choisie par defaut,
    serait l'invention que l'article 17 interdit. La valorisation sort donc
    `EMPTY` et n'evalue aucun lot.
    """
    contenu = valorisation(None)
    assert contenu["mark_population"] == "EMPTY"
    positions = contenu["positions_by_currency"]
    valorisees = [
        lot
        for bloc in (positions.values() if isinstance(positions, dict) else [])
        for lot in (bloc.get("lots", []) if isinstance(bloc, dict) else [])
    ]
    assert valorisees == [], "une marque non qualifiable ne doit valoriser aucun lot"


def test_une_nature_non_textuelle_echoue_aussi_ferme() -> None:
    """Un nombre a la place d'une etiquette n'est pas une nature.

    Meme traitement que l'absence : rien n'est valorise. Une coercition
    silencieuse (`str(42)`) fabriquerait une etiquette que personne n'a ecrite.
    """
    assert valorisation(42)["mark_population"] == "EMPTY"


def test_la_nature_relayee_n_est_jamais_inventee_par_le_worker() -> None:
    """Le worker RELAIE ; il ne juge pas le vocabulaire.

    Le vocabulaire ferme (`POPULATION_LABELS`) appartient a la frontiere API,
    qui refuse une etiquette hors contrat au moment du relais. Le dupliquer ici
    creerait un SECOND proprietaire de la meme verite — ce que
    `.claude/rules/architecture.md` interdit — et un import inverse
    worker -> api par-dessus le marche.
    """
    assert valorisation("USER_DECLARED")["mark_population"] == "USER_DECLARED"
