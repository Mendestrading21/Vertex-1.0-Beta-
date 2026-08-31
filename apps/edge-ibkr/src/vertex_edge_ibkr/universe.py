"""Univers d'abonnement IBKR : borné, explicite, jamais deviné.

POURQUOI CE FICHIER EXISTE. `EntitlementProbe` exige déjà un `con_id` exact et
refuse toute ambiguïté (« Si l'identité ou la session est ambiguë, la sonde
s'arrête »). Une ingestion CONTINUE a besoin de la même garantie, mais pour
plusieurs instruments et sur la durée. Sans univers déclaré, la première boucle
aurait choisi des symboles « populaires » et FABRIQUÉ une identité — exactement
ce que `docs/04-integrations/IBKR_ENTITLEMENT_PROBE.md` interdit.

CE QU'IL NE FAIT JAMAIS
-----------------------
- Aucun symbole par défaut : sans fichier d'univers, l'ingestion ne démarre pas.
- Aucune résolution réseau : un `con_id` absent est un REFUS, pas une requête.
  Résoudre ici reviendrait à qualifier un contrat sans supervision humaine.
- Aucun univers non borné : au-delà de `MAX_UNIVERSE_SIZE`, refus explicite.
  `LineBudget` protège déjà la session côté lignes de données ; cette borne-ci
  protège le budget de MESSAGES avant même la connexion.
- Aucun `strike` en flottant : la valeur est lue en `Decimal` depuis sa forme
  textuelle exacte, jamais via `float`.

FORMAT (JSON — bibliothèque standard, aucune dépendance ajoutée) ::

    {
      "instruments": [
        {"con_id": 265598, "sec_type": "STK", "symbol": "XYZ",
         "exchange": "SMART", "currency": "USD"}
      ]
    }

Le fichier vit HORS du dépôt : il nomme les instruments réellement suivis par
l'utilisateur, ce qui est une donnée personnelle.
"""

from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from vertex_edge_ibkr.port import ContractSpec

__all__ = [
    "MAX_HISTORICAL_UNIVERSE_SIZE",
    "MAX_UNIVERSE_SIZE",
    "UniverseError",
    "load_universe",
    "parse_universe",
]

#: Borne du régime TEMPS RÉEL. Chaque instrument abonné consomme une ligne de
#: données de marché, et IBKR n'en accorde qu'une centaine : c'est cette
#: ressource-là qui contraint, pas le temps.
MAX_UNIVERSE_SIZE = 24

#: Borne du régime HISTORIQUE. `reqHistoricalData` ne consomme AUCUNE ligne :
#: sa seule limite est le pacing (60 requêtes par fenêtre de 10 minutes, soit
#: ~6/min). Des milliers de titres sont donc possibles — en heures, pas en
#: secondes. Appliquer ici le plafond du temps réel interdirait le régime pour
#: une raison qui ne s'y applique pas.
MAX_HISTORICAL_UNIVERSE_SIZE = 5000

#: Clés reconnues. Une clé inconnue est un refus : une faute de frappe sur
#: `trading_class` produirait sinon un contrat silencieusement différent.
_ALLOWED_KEYS = frozenset(
    {
        "con_id",
        "sec_type",
        "symbol",
        "exchange",
        "currency",
        "last_trade_date",
        "strike",
        "right",
        "trading_class",
        "multiplier",
        "local_symbol",
    }
)


class UniverseError(ValueError):
    """Univers absent, illisible, ambigu, incomplet ou hors borne."""


def _require_con_id(raw: Any, index: int) -> int:
    if not isinstance(raw, int) or isinstance(raw, bool) or raw <= 0:
        raise UniverseError(
            f"instrument #{index} : `con_id` entier strictement positif requis. "
            "Un symbole seul n'est JAMAIS une identité — utiliser d'abord "
            "`tools/probe_entitlements.py --symbol <X> --dry-run` pour le relever."
        )
    return raw


def _optional_str(entry: dict[str, Any], key: str, index: int) -> str | None:
    value = entry.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise UniverseError(f"instrument #{index} : `{key}` doit être une chaîne non vide.")
    return value


def _optional_strike(entry: dict[str, Any], index: int) -> Decimal | None:
    value = entry.get("strike")
    if value is None:
        return None
    if isinstance(value, float):
        raise UniverseError(
            f"instrument #{index} : `strike` en flottant refusé — écrire la valeur "
            'exacte sous forme de chaîne, par exemple "187.5".'
        )
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as erreur:
        raise UniverseError(f"instrument #{index} : `strike` illisible ({value!r}).") from erreur


def _parse_entry(entry: Any, index: int) -> ContractSpec:
    if not isinstance(entry, dict):
        raise UniverseError(f"instrument #{index} : objet JSON attendu.")
    inconnues = sorted(set(entry) - _ALLOWED_KEYS)
    if inconnues:
        raise UniverseError(
            f"instrument #{index} : clés inconnues {inconnues}. "
            f"Clés reconnues : {sorted(_ALLOWED_KEYS)}."
        )
    sec_type = _optional_str(entry, "sec_type", index)
    if sec_type is None:
        raise UniverseError(f"instrument #{index} : `sec_type` requis (STK, OPT, IND...).")
    try:
        return ContractSpec(
            sec_type=sec_type,
            con_id=_require_con_id(entry.get("con_id"), index),
            symbol=_optional_str(entry, "symbol", index),
            exchange=_optional_str(entry, "exchange", index),
            currency=_optional_str(entry, "currency", index),
            last_trade_date=_optional_str(entry, "last_trade_date", index),
            strike=_optional_strike(entry, index),
            right=_optional_str(entry, "right", index),
            trading_class=_optional_str(entry, "trading_class", index),
            multiplier=_optional_str(entry, "multiplier", index),
            local_symbol=_optional_str(entry, "local_symbol", index),
        )
    except ValueError as erreur:
        if isinstance(erreur, UniverseError):
            raise
        raise UniverseError(f"instrument #{index} : {erreur}") from erreur


def parse_universe(
    document: Any, *, max_size: int = MAX_UNIVERSE_SIZE
) -> tuple[ContractSpec, ...]:
    """Valide un document d'univers déjà décodé et rend des contrats exacts.

    Refuse : document non-objet, `instruments` absent ou vide, taille au-delà
    de ``max_size``, `con_id` absent ou dupliqué. Un univers vide n'est pas un
    univers neutre — c'est une configuration incomplète, donc un refus.
    """
    if max_size < 1 or max_size > MAX_HISTORICAL_UNIVERSE_SIZE:
        raise UniverseError(
            f"max_size doit rester dans [1, {MAX_HISTORICAL_UNIVERSE_SIZE}]. "
            f"Le régime temps réel, lui, ne dépasse jamais {MAX_UNIVERSE_SIZE} "
            "(une ligne de données par instrument)."
        )
    if not isinstance(document, dict):
        raise UniverseError("univers : objet JSON attendu à la racine.")
    instruments = document.get("instruments")
    if not isinstance(instruments, list) or not instruments:
        raise UniverseError("univers : `instruments` doit être une liste non vide.")
    if len(instruments) > max_size:
        raise UniverseError(
            f"univers : {len(instruments)} instruments demandés, maximum {max_size}. "
            "Le budget de messages IBKR est volontairement borné."
        )
    specs = tuple(_parse_entry(entry, index) for index, entry in enumerate(instruments))
    con_ids = [spec.con_id for spec in specs]
    doublons = sorted({c for c in con_ids if con_ids.count(c) > 1 and c is not None})
    if doublons:
        raise UniverseError(f"univers : `con_id` dupliqués {doublons} — identité ambiguë.")
    return specs


def load_universe(path: Path, *, max_size: int = MAX_UNIVERSE_SIZE) -> tuple[ContractSpec, ...]:
    """Lit et valide le fichier d'univers. Toute anomalie arrête l'ingestion."""
    try:
        texte = path.read_text(encoding="utf-8")
    except OSError as erreur:
        raise UniverseError(f"univers illisible ({path}) : {erreur}") from erreur
    try:
        document = json.loads(texte)
    except json.JSONDecodeError as erreur:
        raise UniverseError(f"univers : JSON invalide ({path}) : {erreur}") from erreur
    return parse_universe(document, max_size=max_size)
