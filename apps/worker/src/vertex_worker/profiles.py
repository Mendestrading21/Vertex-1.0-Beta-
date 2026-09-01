"""Profils de fusion : ce qui a le droit d'atteindre l'écran.

POURQUOI CE FICHIER EXISTE. Les six registres de fusion du worker sont
**deny-by-default** : `calendar.py:595` refuse toute observation dont la
`source` ou les `rights` ne sont pas explicitement déclarés. Or le dépôt ne
contenait qu'une seule famille de registres — `DEV_SYNTHETIC_*` — n'autorisant
que `synthetic-dev` / `SYNTHETIC`.

Conséquence mesurée : une observation IBKR (`source="ibkr"`,
`rights="IBKR_MARKET_DATA_DISPLAY_ONLY"`) entrait bien en base, puis était
refusée à la fusion. Aucun snapshot publié, aucune page modifiée. L'ingestion
tournait, les compteurs montaient, et l'écran ne bougeait pas.

Ce n'était pas un défaut : c'est la garantie « rien de non déclaré n'atteint
l'écran ». Il manquait simplement la déclaration du réel. Ce fichier la porte,
en un seul endroit, explicitement.

CE QU'IL NE FAIT PAS
--------------------
- Il n'ouvre RIEN par défaut : le profil `synthetic` reste celui du démarrage.
  Passer au réel exige `VERTEX_FUSION_PROFILE=real` ET un univers déclaré.
- Il n'invente aucun secteur. Vertex n'a aujourd'hui AUCUNE source de
  classification sectorielle pour des instruments réels ; répartir les
  con_id dans des secteurs plausibles serait une fabrication. Tous les
  instruments réels vivent donc dans un secteur unique, honnêtement nommé.
- Il ne PROMEUT pas IBKR en confiance. Le niveau reste
  `DEFAULT_SOURCE_TIER`, le plus bas, faute d'échelle de confiance déclarée
  quelque part. Accorder un niveau supérieur sans registre reviendrait à
  inventer une autorité.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from vertex_core.contracts.market_quote import (
    UNCLASSIFIED_SECTOR_CODE,
    UNCLASSIFIED_SECTOR_LABEL,
)
from vertex_worker.analysis import DEV_SYNTHETIC_ANALYSIS_CONFIG, AnalysisConfig
from vertex_worker.calendar import DEV_SYNTHETIC_CALENDAR_CONFIG, CalendarConfig
from vertex_worker.handlers import (
    DEFAULT_SOURCE_TIER,
    DEV_SYNTHETIC_CONFIG,
    FusionConfig,
)
from vertex_worker.markets import DEV_SYNTHETIC_MARKETS_CONFIG, MarketsConfig
from vertex_worker.opportunities import (
    DEV_SYNTHETIC_OPPORTUNITIES_CONFIG,
)
from vertex_worker.options import DEV_SYNTHETIC_OPTIONS_CONFIG, OptionsConfig
from vertex_worker.risk import DEV_SYNTHETIC_RISK_CONFIG, RiskConfig

__all__ = [
    "IBKR_RIGHTS",
    "IBKR_SOURCE",
    "PROFILE_ENV_VAR",
    "PROFILE_REAL",
    "PROFILE_SYNTHETIC",
    "REAL_LOOKBACK",
    "REAL_SECTOR_CODE",
    "REAL_SECTOR_LABEL",
    "ProfileError",
    "RealInstrument",
    "WorkerProfile",
    "load_real_instruments",
    "real_ibkr_profile",
    "resolve_profile",
    "synthetic_profile",
]

#: Identité de la source réelle, telle que l'adaptateur l'estampille.
IBKR_SOURCE = "ibkr"
IBKR_RIGHTS = "IBKR_MARKET_DATA_DISPLAY_ONLY"

#: Secteur unique des instruments réels. Déclaré dans `vertex_core` parce que
#: l'edge le PRODUIT dans la charge utile et que le worker le RELIT : deux
#: constantes séparées dériveraient, et la page Marchés deviendrait vide sans
#: message d'erreur. Ce n'est pas un secteur, c'est l'aveu qu'il n'y en a pas.
REAL_SECTOR_CODE = UNCLASSIFIED_SECTOR_CODE
REAL_SECTOR_LABEL = UNCLASSIFIED_SECTOR_LABEL

PROFILE_ENV_VAR = "VERTEX_FUSION_PROFILE"
PROFILE_SYNTHETIC = "synthetic"
PROFILE_REAL = "real"

#: Fenêtre de chargement du profil RÉEL. Les 72 h par défaut suffisent à une
#: population synthétique générée en continu ; de vraies clôtures quotidiennes
#: n'existent que les jours ouvrés. Mesuré le 2026-08-31 : la clôture de
#: vendredi (horodatée 02:00 UTC) avait 83 h le lundi midi et disparaissait de
#: la page. 8 jours couvrent un week-end prolongé avec marge.
#:
#: Ce n'est PAS une promesse de fraîcheur : celle-ci reste portée par
#: `stale_after` et par l'âge publié à côté de chaque valeur.
REAL_LOOKBACK = timedelta(days=8)

#: Indice de référence de `market.relative_strength`, déclaré et non deviné.
#: Il n'est appliqué QUE s'il figure réellement dans l'univers collecté :
#: déclarer une référence absente produirait `BENCHMARK_NOT_OBSERVED` sur
#: chaque instrument, une absence bruyante qui n'apprend rien.
#:
#: SPX est le choix le plus large pour un univers d'actions américaines. Pour
#: un univers européen ce serait un autre indice — d'où un champ configurable
#: plutôt qu'une constante gravée dans le calcul.
REFERENCE_BENCHMARK = "SPX"

#: L'univers réel reste borné : la fusion charge un nombre d'observations
#: plafonné, et un univers démesuré produirait une couverture trompeuse.
#: Perimetre DECLARE de la matrice de correlation (page Risques).
#:
#: Huit indices mondiaux, parce qu ils sont LISIBLES : une matrice se lit d un
#: coup d oeil ou ne se lit pas. Comparer les 161 titres collectes ferait deux
#: choses, toutes deux mauvaises — l intersection stricte des calendriers
#: tomberait aux seuls jours ou trois continents cotent ensemble, et une grille
#: 161x161 n est pas un ecran.
#:
#: Comme `REFERENCE_BENCHMARK`, ce perimetre n est applique que si ses membres
#: sont REELLEMENT collectes. Choisir qui se compare a qui est une decision de
#: produit, d ou un champ declare plutot qu une constante gravee dans le calcul.
RISK_PERIMETER: tuple[str, ...] = (
    "SPX",
    "NDX",
    "RUT",
    "VIX",
    "DAX",
    "ESTX50",
    "N225",
    "SMI",
)

#: Libelles francais du perimetre de risque.
RISK_LABELS: dict[str, str] = {
    "SPX": "S&P 500",
    "NDX": "Nasdaq 100",
    "RUT": "Russell 2000",
    "VIX": "Volatilite S&P",
    "DAX": "DAX 40",
    "ESTX50": "Euro Stoxx 50",
    "N225": "Nikkei 225",
    "SMI": "SMI Suisse",
}

#: Deux instruments au minimum : une matrice de correlation COMPARE.
MINIMUM_RISK_PERIMETER = 2

MAX_REAL_INSTRUMENTS = 500


class ProfileError(ValueError):
    """Profil inconnu, univers absent, illisible ou vide."""


@dataclass(frozen=True)
class RealInstrument:
    """Un instrument réel porte DEUX identifiants, pour deux usages distincts.

    ``ref`` est ``str(con_id)`` : c'est ce que l'adaptateur estampille dans
    ``instrument_id``, et ce sur quoi l'analyse, les options et le calendrier
    apparient. ``symbol`` est ce que la page Marchés AFFICHE et compare à son
    univers déclaré (`markets.py::_parse_quote` exige
    ``ticker ∈ universe[sector]``).

    Ce ne sont pas deux vérités contradictoires : l'ambiguïté d'un symbole
    (32 contrats « GOOG » chez IBKR) est tranchée en amont par le ``con_id``
    du fichier d'univers. L'écran n'a pas à la reporter.
    """

    ref: str
    symbol: str


@dataclass(frozen=True)
class WorkerProfile:
    """Les six registres qui décident de ce qui atteint l'écran."""

    name: str
    fusion: FusionConfig
    markets: MarketsConfig
    options: OptionsConfig
    analysis: AnalysisConfig
    calendar: CalendarConfig
    opportunities: AnalysisConfig
    #: `None` quand le perimetre declare n est pas collecte : la page
    #: Risques reste alors vide EN LE DISANT, plutot que de comparer
    #: des instruments choisis au hasard pour la remplir.
    risk: RiskConfig | None = None

    @property
    def is_real(self) -> bool:
        return self.name == PROFILE_REAL


def synthetic_profile() -> WorkerProfile:
    """Profil de développement : rien d'autre que la population SYNTHETIC."""
    return WorkerProfile(
        name=PROFILE_SYNTHETIC,
        fusion=DEV_SYNTHETIC_CONFIG,
        markets=DEV_SYNTHETIC_MARKETS_CONFIG,
        options=DEV_SYNTHETIC_OPTIONS_CONFIG,
        analysis=DEV_SYNTHETIC_ANALYSIS_CONFIG,
        calendar=DEV_SYNTHETIC_CALENDAR_CONFIG,
        opportunities=DEV_SYNTHETIC_OPPORTUNITIES_CONFIG,
        risk=DEV_SYNTHETIC_RISK_CONFIG,
    )


def real_ibkr_profile(instruments: Sequence[RealInstrument]) -> WorkerProfile:
    """Profil réel : la source IBKR déclarée, sur un univers explicite.

    Ce sont exactement les instruments ingérés : ce qu'on collecte est ce
    qu'on analyse. Chacun porte sa référence (``str(con_id)``, appariée sur
    ``instrument_id``) et son symbole (affiché et apparié par la page Marchés).
    """
    if not instruments:
        raise ProfileError(
            "profil réel : univers vide. Aucun instrument n'est deviné — "
            "l'écran resterait vide sans le dire."
        )
    if len(instruments) > MAX_REAL_INSTRUMENTS:
        raise ProfileError(
            f"profil réel : {len(instruments)} instruments, maximum "
            f"{MAX_REAL_INSTRUMENTS}. Au-delà, la couverture publiée cesse "
            "d'être significative."
        )
    uniques: dict[str, RealInstrument] = {}
    for position, instrument in enumerate(instruments):
        if not isinstance(instrument, RealInstrument):
            # Une AttributeError en profondeur ne dit pas quoi corriger.
            raise ProfileError(
                f"instrument #{position} : RealInstrument attendu, recu "
                f"{type(instrument).__name__}. Un instrument reel porte DEUX "
                "identifiants : `ref` (con_id, pour l'identite) et `symbol` "
                "(pour l'affichage)."
            )
    for instrument in instruments:
        uniques.setdefault(instrument.ref, instrument)  # dédoublonne, ordre gardé
    # TOUTES les pages comparent un TICKER porte par la charge utile
    # (`payload['ticker']`, `payload['underlying']`) a leur univers
    # declare — jamais `instrument_id`. Ces configs portent donc les
    # SYMBOLES. Le `con_id` reste l'identite technique : il dedoublonne
    # ci-dessus et voyage dans `instrument_id`, sans jamais atteindre
    # l'ecran ni les URL.
    symboles = tuple(dict.fromkeys(i.symbol for i in uniques.values()))
    sources = frozenset({IBKR_SOURCE})
    droits = frozenset({IBKR_RIGHTS})
    # Meme regle que l indice de reference : declare ne veut pas dire
    # present. On ne retient que les membres REELLEMENT collectes, et
    # au-dessous de deux il n y a rien a comparer.
    perimetre_risque = tuple(t for t in RISK_PERIMETER if t in symboles)
    registre_risque = (
        RiskConfig(
            perimeter=perimetre_risque,
            labels={t: RISK_LABELS.get(t, t) for t in perimetre_risque},
            allowed_sources=sources,
            usable_rights=droits,
        )
        if len(perimetre_risque) >= MINIMUM_RISK_PERIMETER
        else None
    )
    return WorkerProfile(
        name=PROFILE_REAL,
        fusion=FusionConfig(
            allowed_sources=sources,
            usable_rights=droits,
            lookback=REAL_LOOKBACK,
            # Niveau de confiance NON promu : voir l'en-tête du module.
            source_tiers={IBKR_SOURCE: DEFAULT_SOURCE_TIER},
        ),
        markets=MarketsConfig(
            # La page Marchés compare `payload['ticker']` à cet univers :
            # elle doit donc porter les SYMBOLES, pas les con_id.
            universe={REAL_SECTOR_CODE: symboles},
            sector_labels={REAL_SECTOR_CODE: REAL_SECTOR_LABEL},
            allowed_sources=sources,
            usable_rights=droits,
            lookback=REAL_LOOKBACK,
        ),
        options=OptionsConfig(
            underlyings=symboles,
            allowed_sources=sources,
            usable_rights=droits,
        ),
        analysis=AnalysisConfig(
            instruments=symboles,
            allowed_sources=sources,
            usable_rights=droits,
            lookback=REAL_LOOKBACK,
            # Déclaré SEULEMENT s'il est réellement collecté : une référence
            # absente rendrait `BENCHMARK_NOT_OBSERVED` partout.
            benchmark=REFERENCE_BENCHMARK if REFERENCE_BENCHMARK in symboles else None,
        ),
        calendar=CalendarConfig(
            allowed_sources=sources,
            usable_rights=droits,
            watchlist=symboles,
        ),
        opportunities=AnalysisConfig(
            instruments=symboles,
            allowed_sources=sources,
            usable_rights=droits,
            lookback=REAL_LOOKBACK,
            # Mêmes exigences que le profil de développement : l'horizon
            # déclaré du profil equity_etf_swing_3_12m, et la porte 7
            # réellement OBSERVÉE — jamais satisfaite par déclaration.
            horizon=DEV_SYNTHETIC_OPPORTUNITIES_CONFIG.horizon,
            portfolio_risk_required=DEV_SYNTHETIC_OPPORTUNITIES_CONFIG.portfolio_risk_required,
        ),
        risk=registre_risque,
    )


def load_real_instruments(path: Path) -> tuple[RealInstrument, ...]:
    """Références d'instrument lues dans le fichier d'univers d'ingestion.

    Le même fichier sert à l'ingestion et à la fusion : ce qu'on collecte est
    ce qu'on analyse. Seuls les ``con_id`` sont lus ici — la validation
    complète du contrat appartient à ``vertex_edge_ibkr.universe``, et la
    dupliquer créerait deux vérités.
    """
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except OSError as erreur:
        raise ProfileError(f"univers illisible ({path}) : {erreur}") from erreur
    except json.JSONDecodeError as erreur:
        raise ProfileError(f"univers : JSON invalide ({path}) : {erreur}") from erreur
    if not isinstance(document, dict):
        raise ProfileError("univers : objet JSON attendu à la racine.")
    entrees = document.get("instruments")
    if not isinstance(entrees, list) or not entrees:
        raise ProfileError("univers : `instruments` doit être une liste non vide.")
    lus: list[RealInstrument] = []
    for index, entree in enumerate(entrees):
        if not isinstance(entree, dict):
            raise ProfileError(f"instrument #{index} : objet JSON attendu.")
        con_id = entree.get("con_id")
        if not isinstance(con_id, int) or isinstance(con_id, bool) or con_id <= 0:
            raise ProfileError(f"instrument #{index} : `con_id` entier strictement positif requis.")
        symbol = entree.get("symbol")
        if not isinstance(symbol, str) or not symbol.strip():
            # Sans symbole, la cotation n'appartiendrait à aucun univers
            # declaré et serait rejetée à l'affichage sans que personne sache
            # pourquoi. On refuse ici, en nommant le contrat fautif.
            raise ProfileError(
                f"instrument #{index} (con_id={con_id}) : `symbol` requis pour le "
                "profil réel — c'est lui que la page Marchés affiche et compare "
                "à son univers déclaré."
            )
        lus.append(RealInstrument(ref=str(con_id), symbol=symbol))
    return tuple(lus)


def resolve_profile(env: Mapping[str, str]) -> WorkerProfile:
    """Choisit le profil depuis l'environnement. Défaut : synthétique.

    Le réel ne s'active jamais par omission : il exige à la fois le nom du
    profil ET un univers déclaré.
    """
    nom = env.get(PROFILE_ENV_VAR, "").strip().lower() or PROFILE_SYNTHETIC
    if nom == PROFILE_SYNTHETIC:
        return synthetic_profile()
    if nom != PROFILE_REAL:
        raise ProfileError(
            f"{PROFILE_ENV_VAR}={nom!r} inconnu. Valeurs acceptées : "
            f"{PROFILE_SYNTHETIC!r} (défaut) ou {PROFILE_REAL!r}."
        )
    brut = env.get("VERTEX_IBKR_UNIVERSE", "").strip()
    if not brut:
        raise ProfileError(
            f"{PROFILE_ENV_VAR}=real exige VERTEX_IBKR_UNIVERSE : le profil réel "
            "n'analyse que des instruments explicitement déclarés."
        )
    return real_ibkr_profile(load_real_instruments(Path(brut).expanduser()))
