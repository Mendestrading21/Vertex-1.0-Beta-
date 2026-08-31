"""Fenêtre glissante du pacing historique IBKR.

CE QUE CES TESTS EMPÊCHENT. Confondre une fenêtre glissante avec un débit
moyen. `MessagePacer` (seau à jetons, 38/s) accepterait 60 requêtes
historiques en deux secondes — largement sous son débit — et IBKR répondrait
immédiatement par une violation de pacing. La fenêtre glissante, elle, exige
d'attendre que la PLUS ANCIENNE requête sorte de la fenêtre.

L'horloge est injectée et pilotée à la main : aucun test n'attend le temps réel.
"""

from __future__ import annotations

import pytest

from vertex_edge_ibkr.pacing import (
    DEFAULT_HISTORICAL_REQUESTS_PER_WINDOW,
    DEFAULT_HISTORICAL_WINDOW_SECONDS,
    SlidingWindowPacer,
)


class Horloge:
    """Horloge monotone pilotée : le temps n'avance que si on le demande."""

    def __init__(self, depart: float = 0.0) -> None:
        self.maintenant = depart

    def __call__(self) -> float:
        return self.maintenant

    def avancer(self, secondes: float) -> None:
        self.maintenant += secondes


def pacer(
    horloge: Horloge, *, max_requests: int = 3, window: float = 100.0, cooldown: float = 0.0
) -> SlidingWindowPacer:
    return SlidingWindowPacer(
        max_requests=max_requests,
        window_seconds=window,
        identical_cooldown_seconds=cooldown,
        clock=horloge,
    )


# -- fenêtre globale -------------------------------------------------------


def test_sous_la_limite_tout_passe() -> None:
    h = Horloge()
    p = pacer(h)
    assert all(p.try_acquire(f"k{i}") for i in range(3))
    assert p.granted == 3
    assert p.deferred == 0


def test_a_la_limite_la_suivante_est_differee() -> None:
    h = Horloge()
    p = pacer(h)
    for i in range(3):
        p.try_acquire(f"k{i}")
    assert p.try_acquire("k4") is False
    assert p.deferred == 1
    assert p.seconds_until_allowed("k4") > 0


def test_le_delai_correspond_a_la_sortie_de_la_PLUS_ANCIENNE() -> None:
    """C'est LA propriété d'une fenêtre glissante, et ce qu'un seau à jetons rate."""
    h = Horloge()
    p = pacer(h, max_requests=2, window=100.0)
    p.try_acquire("a")           # t=0
    h.avancer(30)
    p.try_acquire("b")           # t=30
    h.avancer(10)                # t=40, fenêtre pleine
    # La plus ancienne (t=0) sort à t=100 : il reste 60 s.
    assert p.seconds_until_allowed("c") == pytest.approx(60.0)


def test_apres_glissement_la_place_se_libere() -> None:
    h = Horloge()
    p = pacer(h, max_requests=2, window=100.0)
    p.try_acquire("a")
    p.try_acquire("b")
    assert p.try_acquire("c") is False
    h.avancer(100.1)             # les deux sortent de la fenêtre
    assert p.in_window == 0
    assert p.try_acquire("c") is True


def test_une_rafale_n_est_pas_lissee_en_debit_moyen() -> None:
    """60 requêtes en 1 seconde saturent la fenêtre pour 10 minutes."""
    h = Horloge()
    p = SlidingWindowPacer(max_requests=60, window_seconds=600.0, clock=h)
    for i in range(60):
        assert p.try_acquire(f"s{i}") is True
    h.avancer(1.0)
    assert p.try_acquire("s60") is False
    assert p.seconds_until_allowed("s60") == pytest.approx(599.0)


# -- délai entre requêtes identiques --------------------------------------


def test_deux_requetes_identiques_respectent_le_delai() -> None:
    h = Horloge()
    p = pacer(h, max_requests=100, cooldown=15.0)
    assert p.try_acquire("meme") is True
    assert p.try_acquire("meme") is False
    h.avancer(14.9)
    assert p.try_acquire("meme") is False
    h.avancer(0.2)
    assert p.try_acquire("meme") is True


def test_une_cle_differente_n_est_pas_bloquee_par_le_delai() -> None:
    h = Horloge()
    p = pacer(h, max_requests=100, cooldown=15.0)
    p.try_acquire("aaa")
    assert p.try_acquire("bbb") is True


def test_le_MAXIMUM_des_deux_contraintes_est_retenu() -> None:
    """Prendre le minimum laisserait passer une violation."""
    h = Horloge()
    p = SlidingWindowPacer(
        max_requests=1, window_seconds=100.0, identical_cooldown_seconds=10.0, clock=h
    )
    p.try_acquire("x")
    # fenêtre : 100 s restantes ; cooldown de la clé : 10 s. Le max = 100.
    assert p.seconds_until_allowed("x") == pytest.approx(100.0)


# -- refus de configuration ------------------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "motif"),
    [
        ({"max_requests": 0}, "max_requests"),
        ({"window_seconds": 0.0}, "window_seconds"),
        ({"identical_cooldown_seconds": -1.0}, "identical_cooldown_seconds"),
    ],
)
def test_configuration_invalide_est_refusee(kwargs: dict[str, float], motif: str) -> None:
    with pytest.raises(ValueError, match=motif):
        SlidingWindowPacer(clock=Horloge(), **kwargs)  # type: ignore[arg-type]


def test_une_horloge_implicite_est_refusee() -> None:
    """Aucune source de temps implicite : les tests doivent rester déterministes."""
    with pytest.raises(ValueError, match="clock"):
        SlidingWindowPacer()


# -- valeurs par défaut = celles d'IBKR ------------------------------------


def test_les_defauts_correspondent_au_pacing_publie_par_ibkr() -> None:
    assert DEFAULT_HISTORICAL_REQUESTS_PER_WINDOW == 60
    assert DEFAULT_HISTORICAL_WINDOW_SECONDS == 600.0
    p = SlidingWindowPacer(clock=Horloge())
    assert p.capacity == 60


def test_le_debit_soutenable_est_bien_de_six_par_minute() -> None:
    """60 requêtes / 10 min = 6/min. C'est ce qui donne ~2 h 47 pour 1000 titres."""
    h = Horloge()
    p = SlidingWindowPacer(max_requests=60, window_seconds=600.0, clock=h)
    accordees = 0
    # Une heure simulée, une tentative par seconde.
    for _ in range(3600):
        if p.try_acquire(f"t{p.granted}"):
            accordees += 1
        h.avancer(1.0)
    # 6/min sur 60 min = 360, plus la rafale initiale de la première fenêtre.
    assert 360 <= accordees <= 420
