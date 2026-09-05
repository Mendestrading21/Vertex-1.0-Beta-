"""Reprise périodique du remplissage historique.

POURQUOI CE MODE EXISTE. `tools/run_edge_history.py` fait UNE passe sur
l'univers, puis sort. C'est le bon défaut pour un premier remplissage. Mais
Vertex n'a AUCUN ordonnanceur (`docs/99-status/DEBT.md`) : une fois la passe
terminée, plus rien ne remet de travail en file, le worker n'a plus rien à
publier, et les pages restent figées sur l'instantané du moment. L'utilisateur
devait relancer la commande à la main, indéfiniment.

CE QUE CE MODE N'EST PAS. Ce n'est pas un ordonnanceur, ni un service, ni une
dépendance nouvelle : c'est un paramètre du même outil, qui refait la même
passe. `architecture.md` interdit d'ajouter un framework sans ADR ; un
intervalle de reprise n'en est pas un.

FAIL-CLOSED. Le mode est OPT-IN : sans la variable, le comportement d'origine
est exactement conservé. Une valeur non entière, nulle, négative ou sous le
plancher est REFUSÉE — jamais corrigée en silence.
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_OUTIL = _REPO_ROOT / "tools" / "run_edge_history.py"


def _charger() -> Any:
    spec = importlib.util.spec_from_file_location("run_edge_history_tool", _OUTIL)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def outil() -> Any:
    return _charger()


class TestIntervalleDeReprise:
    def test_absent_vaut_passe_unique(self, outil: Any, monkeypatch: Any) -> None:
        """Sans la variable, le comportement d'origine est conservé."""
        monkeypatch.delenv("VERTEX_IBKR_REPEAT_SECONDS", raising=False)
        assert outil.repeat_seconds() is None

    def test_vide_vaut_passe_unique(self, outil: Any, monkeypatch: Any) -> None:
        monkeypatch.setenv("VERTEX_IBKR_REPEAT_SECONDS", "   ")
        assert outil.repeat_seconds() is None

    def test_valeur_admise(self, outil: Any, monkeypatch: Any) -> None:
        monkeypatch.setenv("VERTEX_IBKR_REPEAT_SECONDS", "900")
        assert outil.repeat_seconds() == 900

    @pytest.mark.parametrize("brut", ["0", "-1", "abc", "3.5", "60"])
    def test_valeurs_refusees(self, outil: Any, monkeypatch: Any, brut: str) -> None:
        """Refus explicite, jamais une correction silencieuse.

        `60` est refusé parce qu'il est SOUS le plancher : IBKR n'accorde que
        60 requêtes par fenêtre glissante de dix minutes, donc une passe de K
        instruments ne peut pas durer moins de K/6 minutes. Repartir plus vite
        que le plancher ne collecte rien de plus — cela ne produit que des
        reconnexions et du bruit de journal.
        """
        monkeypatch.setenv("VERTEX_IBKR_REPEAT_SECONDS", brut)
        with pytest.raises(SystemExit) as sortie:
            outil.repeat_seconds()
        assert sortie.value.code == 2

    def test_plancher_documente(self, outil: Any) -> None:
        assert outil.MIN_REPEAT_SECONDS == 300


class TestBoucleDePasses:
    def test_sans_intervalle_une_seule_passe(self, outil: Any) -> None:
        passes: list[int] = []

        async def session() -> str:
            passes.append(1)
            return "stats"

        dormi: list[float] = []

        async def dormir(secondes: float) -> None:
            dormi.append(secondes)

        resultat = asyncio.run(
            outil.run_passes(
                session=session,
                repeat_seconds=None,
                arret_demande=lambda: False,
                sleep=dormir,
            )
        )
        assert passes == [1]
        assert dormi == []
        assert resultat == 1

    def test_avec_intervalle_repasse_et_dort_entre_deux(self, outil: Any) -> None:
        passes: list[int] = []
        dormi: list[float] = []

        async def session() -> str:
            passes.append(len(passes) + 1)
            return "stats"

        async def dormir(secondes: float) -> None:
            dormi.append(secondes)

        # Arrêt demandé APRÈS la troisième passe.
        def arret() -> bool:
            return len(passes) >= 3

        resultat = asyncio.run(
            outil.run_passes(
                session=session,
                repeat_seconds=900,
                arret_demande=arret,
                sleep=dormir,
            )
        )
        assert passes == [1, 2, 3]
        assert dormi == [900.0, 900.0], "une attente entre deux passes, aucune après la dernière"
        assert resultat == 3

    def test_arret_demande_pendant_l_attente_ne_relance_pas(self, outil: Any) -> None:
        """Un Ctrl-C pendant l'attente ne doit pas déclencher une passe de plus."""
        passes: list[int] = []
        stop = {"demande": False}

        async def session() -> str:
            passes.append(1)
            return "stats"

        async def dormir(_secondes: float) -> None:
            stop["demande"] = True

        resultat = asyncio.run(
            outil.run_passes(
                session=session,
                repeat_seconds=900,
                arret_demande=lambda: stop["demande"],
                sleep=dormir,
            )
        )
        assert passes == [1], "l'arrêt pendant l'attente a été ignoré"
        assert resultat == 1

    def test_une_passe_qui_echoue_arrete_la_boucle(self, outil: Any) -> None:
        """Une erreur n'est jamais avalée pour « continuer quand même »."""

        async def session() -> str:
            raise RuntimeError("transport IBKR perdu")

        async def dormir(_secondes: float) -> None:
            return None

        with pytest.raises(RuntimeError, match="transport IBKR perdu"):
            asyncio.run(
                outil.run_passes(
                    session=session,
                    repeat_seconds=900,
                    arret_demande=lambda: False,
                    sleep=dormir,
                )
            )
