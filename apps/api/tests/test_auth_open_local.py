"""Accès local ouvert (``VERTEX_AUTH_OPEN_LOCAL``) — ce qu'il fait, et ce
qu'il ne fait PAS.

POURQUOI CE DRAPEAU EXISTE. Ajouté le 2026-09-01 à la demande explicite du
propriétaire du poste, qui ne voulait plus saisir de passkey pour ouvrir SON
terminal local, en lecture seule, sur la boucle locale.

CE QUE CES TESTS PROTÈGENT, dans l'ordre d'importance :

1. **La valeur par défaut reste FERMÉE.** Sans la variable, une route
   protégée répond 401 exactement comme avant. C'est le point qui compte le
   plus : une installation existante ne doit pas s'ouvrir toute seule après
   une mise à jour.
2. **Seule la valeur ``"1"`` ouvre.** Ni ``"0"``, ni ``"true"``, ni ``"yes"``,
   ni une chaîne vide. Un drapeau de sécurité qui s'activerait sur une valeur
   approchante posée par mégarde serait pire qu'aucun drapeau.
3. **La session ouverte ne se déguise pas.** ``established_via`` vaut
   ``LOCAL_OPEN``, jamais ``WEBAUTHN`` : un journal ne doit pas laisser lire
   une authentification là où il n'y en a eu aucune.
"""

from __future__ import annotations

from typing import ClassVar

import pytest
from fastapi.testclient import TestClient

from vertex_api.auth.dependencies import (
    OPEN_LOCAL_ENV_VAR,
    OPEN_LOCAL_SUBJECT,
    open_local_access,
    require_session,
)

ROUTE_PROTEGEE = "/api/v1/markets/overview"


class RequeteNue:
    """Une requete SANS rien : ni cookie, ni en-tete, ni application.

    Si  touchait la base ou lisait un cookie, ces appels
    leveraient. Qu'ils aboutissent EST la demonstration que la porte ouverte
    ne depend de rien.
    """

    cookies: ClassVar[dict[str, str]] = {}
    headers: ClassVar[dict[str, str]] = {}

    def __init__(self, method: str = "GET") -> None:
        self.method = method


class TestDrapeau:
    def test_absent_ferme(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Sans la variable, rien n'est ouvert."""
        monkeypatch.delenv(OPEN_LOCAL_ENV_VAR, raising=False)
        assert open_local_access() is False

    @pytest.mark.parametrize(
        "valeur",
        ["", "0", "true", "TRUE", "yes", "oui", "on", " 1", "1 ", "2", "-1"],
    )
    def test_seule_la_valeur_un_ouvre(
        self, monkeypatch: pytest.MonkeyPatch, valeur: str
    ) -> None:
        """Une valeur APPROCHANTE n'ouvre pas.

        « true » posé par habitude n'ouvrirait rien, et c'est voulu : mieux
        vaut un drapeau qui ne s'active pas qu'un drapeau qui s'active sans
        qu'on l'ait décidé.
        """
        monkeypatch.setenv(OPEN_LOCAL_ENV_VAR, valeur)
        assert open_local_access() is False

    def test_la_valeur_un_ouvre(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(OPEN_LOCAL_ENV_VAR, "1")
        assert open_local_access() is True

    def test_lu_a_chaque_appel(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Le drapeau est relu à chaque appel, jamais figé à l'import.

        Figé au chargement du module, son effet dépendrait de l'ordre des
        imports — un comportement de sécurité qui varie selon qui importe
        quoi en premier serait impossible à raisonner.
        """
        monkeypatch.delenv(OPEN_LOCAL_ENV_VAR, raising=False)
        assert open_local_access() is False
        monkeypatch.setenv(OPEN_LOCAL_ENV_VAR, "1")
        assert open_local_access() is True
        monkeypatch.delenv(OPEN_LOCAL_ENV_VAR, raising=False)
        assert open_local_access() is False


class TestRouteProtegee:
    def test_ferme_par_defaut_le_401_reste(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """LE TEST QUI COMPTE LE PLUS : rien n'a changé sans la variable."""
        monkeypatch.delenv(OPEN_LOCAL_ENV_VAR, raising=False)
        reponse = client.get(ROUTE_PROTEGEE)
        assert reponse.status_code == 401
        assert reponse.json()["detail"]["code"] == "AUTH_REQUIRED"

    def test_ouvert_la_porte_ne_rend_plus_401(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Avec le drapeau, la dépendance n'oppose plus de 401.

        La vérification porte sur la PORTE, pas sur la route : servir une
        route demanderait une base PostgreSQL, que cette suite unitaire n'a
        pas. Le parcours complet est vérifié contre l'application réelle,
        pas simulé ici.
        """
        monkeypatch.setenv(OPEN_LOCAL_ENV_VAR, "1")


        # Aucune exception : sans le drapeau, ce meme appel leverait un 401
        # faute de cookie de session.
        assert require_session(RequeteNue()).established_via == "LOCAL_OPEN"  # type: ignore[arg-type]

    def test_la_session_ouverte_ne_se_deguise_pas(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``LOCAL_OPEN`` et non ``WEBAUTHN`` : le nom dit la vérité.

        Rendre ``WEBAUTHN`` ferait lire un journal comme une connexion
        réussie alors que rien n'a été vérifié. C'est exactement le genre de
        mensonge que ce dépôt refuse.
        """
        monkeypatch.setenv(OPEN_LOCAL_ENV_VAR, "1")

        # On appelle la dépendance directement : elle ne doit toucher ni
        # cookie, ni base de données.

        contexte = require_session(RequeteNue("POST"))  # type: ignore[arg-type]
        assert contexte.established_via == "LOCAL_OPEN"
        assert contexte.subject == OPEN_LOCAL_SUBJECT

    def test_ouvert_aucune_base_n_est_touchee(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Aucune session n'est lue : la porte ouverte ne dépend de rien.

        Une requête sans cookie, sans en-tête et sans application attachée
        doit passer. Si la dépendance touchait la base, cet appel lèverait.
        """
        monkeypatch.setenv(OPEN_LOCAL_ENV_VAR, "1")


        contexte = require_session(RequeteNue("POST"))  # type: ignore[arg-type]
        assert contexte.established_via == "LOCAL_OPEN"
