"""Propriétaire UNIQUE de la fraîcheur au relais.

POURQUOI CE MODULE EXISTE
-------------------------
`.claude/rules/financial-safety.md` interdit de « conserver SILENCIEUSEMENT un
ancien verdict ». Or huit relais sur dix ne publiaient pas l'âge de ce qu'ils
servaient : un dossier de trois jours arrivait à l'écran exactement comme un
dossier d'une minute. Le défaut est épinglé par
`apps/worker/tests_integration/test_chaos_degradation.py::test_defaut_connu_un_dossier_publie_se_dit_encore_frais_bien_plus_tard`.

Une sonde a mesuré ce qui change le correctif : le TTL déclaré de `daily_bar`
en séance fermée vaut **72 h**. Resserrer un budget ne corrigeait donc rien au
cas mesuré à +71 h, et raccourcir un TTL « pour faire joli » aurait été
exactement la valeur non justifiée que ce dépôt refuse ailleurs. Le correctif
réel est de **publier l'âge dans tous les cas** : à +71 h le dossier est servi
avec ses 255 600 secondes, donc le verdict gelé n'est plus présenté sans sa
date.

CE QUE CE MODULE NE FAIT PAS
----------------------------
- Il n'invente aucun TTL : le budget vient de `FreshnessPolicy`, registre
  versionné possédé par `vertex_core.data.freshness`.
- Il ne décide de rien : il MESURE et renvoie. C'est l'appelant qui choisit de
  refuser, de dégrader ou de servir — les relais n'ont pas tous la même règle
  et les uniformiser en silence changerait leur comportement.
- Il ne lit ni horloge ni base : ``now`` est toujours injecté.
- Il ne valide pas le contenu persisté : `snapshot.as_of` est vérifié par
  `vertex_api.snapshot_views.require_snapshot_as_of`, propriétaire de
  `SnapshotContentError`. Garder cette frontière évite un import cyclique.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from vertex_core.data.freshness import FreshnessPolicy

__all__ = [
    "NO_DRIFT_TOLERANCE",
    "REASON_CLOCK_INCONSISTENT",
    "REASON_SNAPSHOT_STALE",
    "RelayFreshness",
    "closed_session_budget",
    "evaluate_relay_freshness",
]

_ZERO = timedelta(0)

NO_DRIFT_TOLERANCE = _ZERO
"""Tolérance par défaut : aucune. Un relais qui accepte une avance d'horloge
la DÉCLARE, avec sa valeur et sa raison (`opportunities` tolère 5 s)."""

REASON_SNAPSHOT_STALE = (
    "snapshot older than its freshness budget: age {age} s for a budget of "
    "{budget} s ({policy}@{version} closed-session TTL); the worker published "
    "nothing newer"
)
"""Servi à la place de ``reason = None`` quand le budget est dépassé.

Texte identique, mot pour mot, à celui que `calendar.py` et
`opportunities.py` publiaient séparément : la mise en commun ne change aucune
réponse déjà servie.
"""

REASON_CLOCK_INCONSISTENT = (
    "server clock inconsistency: the snapshot is dated {drift} s ahead of the "
    "relay clock, beyond the declared drift tolerance of {tolerance} s. The "
    "verdict cannot be dated, so it is not served. This is a CLOCK problem "
    "between the worker and the API, NOT an invalid snapshot content"
)
"""Servi quand l'instantané est daté plus en avance que deux processus ne
peuvent dériver : on nomme l'HORLOGE, jamais le contenu persisté."""


@dataclass(frozen=True, slots=True)
class RelayFreshness:
    """Ce que le relais SAIT de l'âge de ce qu'il s'apprête à servir.

    ``age_seconds`` est publiable dans TOUS les états datables : c'est la
    valeur dont l'absence faisait passer un dossier de trois jours pour un
    dossier d'une minute. Il est borné à zéro — une avance tolérée n'est
    jamais publiée comme un âge négatif.
    """

    age: timedelta
    age_seconds: int
    stale: bool
    clock_inconsistent: bool
    drift_seconds: int
    stale_reason: str | None
    clock_reason: str | None


def closed_session_budget(policy: FreshnessPolicy) -> timedelta:
    """Budget du relais : le TTL de SÉANCE FERMÉE de la politique.

    Le relais ne connaît aucun état de séance — il sert un instantané, il ne
    sait pas si le marché était ouvert quand le worker l'a publié. Des deux
    TTL, il retient donc le plus permissif, celui de séance fermée : il couvre
    un week-end normal, donc une période calme légitime n'est jamais étiquetée
    périmée à tort. C'est la borne conservatrice, choisie explicitement.
    """
    return timedelta(seconds=policy.ttl_closed_seconds)


def evaluate_relay_freshness(
    as_of: datetime,
    *,
    now: datetime,
    policy: FreshnessPolicy | None,
    drift_tolerance: timedelta = NO_DRIFT_TOLERANCE,
) -> RelayFreshness:
    """Mesure l'âge d'un instantané, et le compare au budget de ``policy``.

    ``as_of`` et ``now`` doivent être avertis (la validation du contenu
    persisté appartient à l'appelant). L'âge est mesuré sur les horodatages
    SERVEUR, jamais sur le contenu : un contenu peut dater sa propre vérité
    métier, il ne date pas sa publication.

    ``policy=None`` est un cas DÉCLARÉ, pas un défaut : la famille servie n'a
    aucun budget au registre, l'âge est donc publié et ``stale`` reste faux.
    C'est le cas de la matrice de capacités, dont la péremption est portée
    champ par champ par le ``expires_at`` de la sonde elle-même. Inventer ici
    un TTL pour cette famille serait exactement la valeur non justifiée que ce
    dépôt refuse ailleurs.

    Une avance de l'instantané sur l'horloge du relais est une réalité à deux
    processus, pas un défaut de contenu. Jusqu'à ``drift_tolerance`` elle est
    absorbée et l'âge borné à zéro ; au-delà, ``clock_inconsistent`` est vrai
    et l'appelant décide — refuser, dégrader ou lever.
    """
    if as_of.tzinfo is None or as_of.tzinfo.utcoffset(as_of) is None:
        raise ValueError("as_of: naive datetime rejected (aware UTC required)")
    if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
        raise ValueError("now: naive datetime rejected (aware UTC required)")
    if drift_tolerance < _ZERO:
        raise ValueError("drift_tolerance: must not be negative")

    signed = now.astimezone(UTC) - as_of.astimezone(UTC)
    if signed < -drift_tolerance:
        lead = int(-signed.total_seconds())
        return RelayFreshness(
            age=_ZERO,
            age_seconds=0,
            stale=False,
            clock_inconsistent=True,
            drift_seconds=lead,
            stale_reason=None,
            clock_reason=REASON_CLOCK_INCONSISTENT.format(
                drift=lead, tolerance=int(drift_tolerance.total_seconds())
            ),
        )

    # Dérive tolérée : l'âge est borné, jamais publié négatif.
    age = signed if signed > _ZERO else _ZERO
    if policy is None:
        # Aucun budget déclaré : l'âge est publié, rien n'est jugé périmé.
        return RelayFreshness(
            age=age,
            age_seconds=int(age.total_seconds()),
            stale=False,
            clock_inconsistent=False,
            drift_seconds=0,
            stale_reason=None,
            clock_reason=None,
        )
    budget = closed_session_budget(policy)
    stale = age > budget
    return RelayFreshness(
        age=age,
        age_seconds=int(age.total_seconds()),
        stale=stale,
        clock_inconsistent=False,
        drift_seconds=0,
        stale_reason=(
            REASON_SNAPSHOT_STALE.format(
                age=int(age.total_seconds()),
                budget=int(budget.total_seconds()),
                policy=policy.name,
                version=policy.version,
            )
            if stale
            else None
        ),
        clock_reason=None,
    )
