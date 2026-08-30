#!/usr/bin/env python3
"""Porte de détection de secrets — locale, déterministe, sans réseau.

Échoue (code 1) si un fichier suivi par Git contient un secret vraisemblable :
clé privée, jeton de fournisseur, JWT, DSN portant un mot de passe non déclaré,
ou affectation d'une valeur à forte entropie à un identifiant de secret.

Principe fail-closed : une catégorie que ce script ne sait pas décider est
signalée, jamais ignorée silencieusement. Les seules exemptions possibles sont
littérales et déclarées dans ``manifests/secret-allowlist.yaml`` avec un motif
écrit ; aucune exemption par expression régulière, par répertoire ou par
extension n'est acceptée.

Ce script ne remplace pas un scanner d'historique : il inspecte l'arbre de
travail suivi, pas les commits antérieurs (voir docs/99-status/DEBT.md).

Limites ASSUMÉES et documentées, à ne pas confondre avec une couverture :

* la détection reste une HEURISTIQUE de forme et d'entropie ; un secret sans
  clé nommante, découpé, encodé (base64, hexadécimal, rot13), stocké dans un
  binaire non listé ou construit à l'exécution n'est pas vu ;
* les scalaires blocs YAML (``clé: |`` / ``clé: >``) sont reconstitués dans
  les fichiers ``.yaml``/``.yml`` uniquement. Dans du YAML EMBARQUÉ — bloc
  clôturé d'un Markdown, heredoc shell, chaîne Python — l'indentation n'a pas
  le sens d'un document YAML et le bloc n'est pas reconstitué ; seules les
  règles à motif fixe (clé privée, jeton de fournisseur, JWT, DSN) s'y
  appliquent, ligne à ligne ;
* une valeur NON quotée n'est traitée comme une donnée que dans un fichier de
  configuration : dans du code, ``token = build_session_token()`` est une
  expression, pas un secret ;
* la reconstitution YAML est textuelle et n'utilise pas d'analyseur : les
  ancres/alias (``*ref``), les clés multi-documents fusionnées et les flux
  JSON multi-lignes ne sont pas résolus.
"""

from __future__ import annotations

import math
import re
import subprocess
import sys
from collections import Counter
from collections.abc import Iterable
from pathlib import Path
from typing import NamedTuple

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST_PATH = REPO_ROOT / "manifests" / "secret-allowlist.yaml"

# Extensions binaires : lues en octets, jamais décodées ni citées.
BINARY_SUFFIXES = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".webp", ".woff", ".woff2", ".ttf", ".otf", ".ico", ".pdf"}
)

MAX_BYTES = 2_000_000


class Rule(NamedTuple):
    code: str
    label: str
    pattern: re.Pattern[str]


RULES: tuple[Rule, ...] = (
    Rule(
        "PRIVATE_KEY",
        "clé privée en clair",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH |PGP )?PRIVATE KEY-----"),
    ),
    Rule("GITHUB_TOKEN", "jeton GitHub", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36,}\b")),
    Rule("SLACK_TOKEN", "jeton Slack", re.compile(r"\bxox[abposr]-[A-Za-z0-9-]{10,}\b")),
    Rule("AWS_ACCESS_KEY", "clé d'accès AWS", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    Rule("GOOGLE_API_KEY", "clé API Google", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    Rule("STRIPE_KEY", "clé Stripe", re.compile(r"\b[sr]k_live_[0-9A-Za-z]{16,}\b")),
    Rule(
        "ANTHROPIC_KEY",
        "clé de fournisseur d'IA",
        re.compile(r"\b(?:sk-ant-|sk-proj-|sk-)[A-Za-z0-9_-]{24,}\b"),
    ),
    Rule(
        "JWT",
        "jeton JWT signé",
        re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
    ),
    Rule(
        "DSN_PASSWORD",
        "mot de passe dans une URL de connexion",
        # Le userinfo d'un URI admet bien plus que ``[A-Za-z0-9._%-]`` : la
        # RFC 3986 y autorise aussi ``~`` et les « sub-delims » ``!$&'()*+,;=``.
        # Un seul ``+`` dans le nom d'utilisateur (``user+ro``, syntaxe courante
        # des rôles en lecture seule) suffisait donc à contourner la règle.
        # ``/``, ``?``, ``#`` et ``@`` restent EXCLUS : ils terminent le
        # userinfo, les admettre ferait déborder le motif sur le chemin.
        re.compile(
            r"\b[a-z][a-z0-9+.-]*://[A-Za-z0-9._~%!$&'()*+,;=-]+:([^@\s/'\"]{4,})@"
        ),
    ),
)

# Identifiants qui, affectés à une valeur à forte entropie, dénoncent un secret.
#
# Le motif couvre les syntaxes RÉELLEMENT présentes dans ce dépôt, et pas
# seulement l'affectation Python : le nom peut être lui-même entre guillemets
# (JSON, YAML à clés quotées) et la valeur peut être NON quotée (YAML, TOML,
# `.env`, ligne de commande). Un détecteur qui n'attrape que `NOM = "valeur"`
# laisse passer `manifests/*.yaml`, `infra/compose/*.yaml`, `.env` et tout
# fichier JSON du dépôt — c'est-à-dire ses propres formats de configuration.
# Un nom qui désigne l'EMPLACEMENT d'un secret (`secret_location`), son
# IDENTIFIANT (`credential_id`) ou son EMPREINTE (`csrf_token_hash`) ne désigne
# pas le secret lui-même : le signaler serait un faux positif systématique, et
# un détecteur qui crie tout le temps n'est plus lu.
#
# Cette exemption porte sur le NOM CAPTURÉ, et sur lui seul. Elle était écrite
# comme un lookahead `(?!.*(?:_location|_path|…)\b)` placé en tête du motif :
# son `.*` balayait TOUTE LA FIN DE LA LIGNE. Un commentaire (`# voir
# data_dir`), ou simplement une AUTRE clé située après le secret
# (`{"client_secret": …, "tenant_id": …}`), désarmait alors la règle — la
# détection dépendait de l'ORDRE DES CLÉS, sur le format JSON minifié que ce
# script dit précisément viser. Le test est désormais fait en Python sur
# `name`, où il ne peut plus déborder hors du nom.
# Suffixes qui désignent une EMPREINTE : un hachage n'est pas réversible, ce
# n'est pas le secret. Exemptés sur le nom seul.
NAME_IS_A_DIGEST = re.compile(r"(?i)_(?:hash|digest|fingerprint|checksum)$")

# Suffixes qui désignent un EMPLACEMENT ou une RÉFÉRENCE. Les exempter sur le
# NOM SEUL suffisait à désarmer la règle : il suffisait de renommer
# `client_secret` en `client_secret_ref` pour qu'un vrai secret passe
# (7e audit). L'exemption dépend donc désormais de ce que la valeur EST.
NAME_IS_A_POINTER = re.compile(
    r"(?i)_(?:location|path|file|dir|name|env|var|ref|id)$"
)

#: Une valeur qui DÉSIGNE au lieu de porter : nom de variable, chemin, URI.
POINTER_VALUE = re.compile(
    r"""(?x)
    ^(?:
        [A-Z][A-Z0-9_]*                  # NOM_DE_VARIABLE_ENV
      | [^\s]*[/\\][^\s]*              # un chemin
      | \$\{?[A-Za-z0-9_]+\}?            # ${VAR}
      | [a-z][a-z0-9+.-]*:[^\s]*         # env:VAR, vault:…, file:…
      | [^\s]+\.[A-Za-z0-9]{1,8}         # quelque.chose.ext
      # Un emplacement peut se DÉCRIRE en mots plutôt que se localiser :
      # `operating_system_secret_store`. Des mots séparés, sans chiffre, ne
      # sont pas de la matière secrète — un secret n'est pas prononçable.
      | [A-Za-z]{2,}(?:[_.\-][A-Za-z]{2,})+
    )$
    """
)


def name_is_not_the_secret(name: str, value: str) -> bool:
    """Le nom exempte-t-il LÉGITIMEMENT cette valeur ?

    Une empreinte est exemptée sur son nom. Un emplacement ne l'est que si la
    valeur ressemble effectivement à un emplacement : sinon, c'est de la
    matière secrète rangée sous un nom rassurant.
    """
    if NAME_IS_A_DIGEST.search(name):
        return True
    if NAME_IS_A_POINTER.search(name):
        return bool(POINTER_VALUE.match(value))
    return False

_SECRET_NAME = r"""[A-Za-z0-9_.-]*
        (?:secret|token|password|passwd|passphrase|api[_-]?key|private[_-]?key|
           credential|client[_-]?secret|access[_-]?key|auth[_-]?key|
           # Clés cryptographiques : leur nom ne contient ni « secret » ni
           # « password », mais leur valeur EST le secret.
           signing[_-]?key|encryption[_-]?key|hmac[_-]?key|secret[_-]?key|
           session[_-]?key|master[_-]?key|signing[_-]?secret|
           # Formes courtes et matière cryptographique dont le nom ne contient
           # ni « secret » ni « password ».
           pwd|salt|pepper|cookie[_-]?key|bearer|nonce[_-]?key|seed[_-]?key)
     [A-Za-z0-9_.-]*"""  # noqa: S105 (motif de DÉTECTION de noms de secrets, pas un secret)

ASSIGNMENT = re.compile(
    r"""(?ix)
    (?P<nq>["\']?)(?P<name>""" + _SECRET_NAME + r""")(?P=nq)
    # `:?` n'est PAS une affectation : c'est l'expansion shell « valeur requise »
    # (`${VAR:?message}`). La traiter comme telle faisait signaler les messages
    # d'erreur des garde-fous eux-mêmes.
    \s*[:=](?!\?)\s*
    (?:
        # Pas de borne HAUTE : elle faisait décrocher la règle sur la
        # LONGUEUR — un secret de 210 caractères entre guillemets était
        # invisible, alors qu'un secret est d'autant plus sérieux qu'il est
        # long. La borne basse reste (16), elle écarte le bruit.
        (?P<quote>["\'])(?P<quoted>[^"\'\n]{16,})(?P=quote)
      | (?P<bare>[^\s"\',;{}\[\]#]{16,200})
    )
    """
)

#: Guillemet OUVRANT sans fermant dans la tranche examinée. Une valeur plus
#: longue que la tranche de découpage n'a pas son guillemet fermant ici : la
#: règle principale ne peut pas la voir, et c'est exactement le cas d'un
#: secret très long. On rapporte alors le préfixe — il suffit à alerter, et il
#: n'est de toute façon jamais reproduit dans le rapport.
UNTERMINATED_ASSIGNMENT = re.compile(
    r"""(?ix)
    (?P<nq>["\']?)(?P<name>""" + _SECRET_NAME + r""")(?P=nq)
    \s*[:=](?!\?)\s*
    ["\'](?P<open>[^"\'\n]{200,})$
    """
)

# Un scalaire bloc YAML ne porte pas sa valeur sur la ligne de la clé :
#
#     password: |
#       la-valeur-reelle
#
# Un scanner strictement ligne à ligne ne voit donc JAMAIS cette valeur, alors
# que c'est la forme naturelle d'un secret multiligne (clé, certificat, mot de
# passe long) dans un `compose.yaml` ou un manifeste. L'en-tête accepte les
# indicateurs de coupe et d'indentation (`|-`, `>+`, `|2`) et un commentaire
# de fin de ligne, tous licites en YAML.
BLOCK_SCALAR_HEADER = re.compile(
    r"""(?ix)
    ^(?P<indent>[ ]*)(?:-[ ]+)?
    (?P<nq>["\']?)(?P<name>""" + _SECRET_NAME + r""")(?P=nq)
    # Un tag YAML peut précéder l'indicateur (`password: !!binary |`) : sans
    # lui, `!!binary` suffisait à masquer le bloc.
    \s*:\s*(?:\![A-Za-z0-9_!:./-]*\s+)?[|>][-+]?[0-9]*\s*(?:\#.*)?$
    """
)

PLACEHOLDER = re.compile(
    r"""(?ix)
    ^(?:
        \$\{?[A-Za-z0-9_]+\}?           # ${VAR} / $VAR
      | \$\{[A-Za-z0-9_]+[:-].*         # ${VAR:?message} / ${VAR:-défaut}
      | [A-Za-z0-9_]+\s+requis\b.*      # message du garde-fou « VAR requis … »
      | \{\{.*\}\}                      # {{ ... }} (gabarit)
      | \{[A-Za-z0-9_]+\}               # {var} (format Python)
      | <[^>]+>                         # <à remplacer>
      | os\.environ.*
      | process\.env.*
      | (?:example|exemple|placeholder|change[_-]?me|redacted|fictif|dummy|
           fake|sample|synthetic|xxx+|todo|à-définir|a-definir)
        [A-Za-z0-9_.-]{0,24}
      | [A-Za-z0-9_.-]{0,24}
        (?:example|exemple|placeholder|change[_-]?me|redacted|fictif|dummy|
           fake|sample|synthetic|todo)
    )$
    """
)

# Deux seuils, parce qu'un seul ne suffit pas. L'entropie PAR CARACTÈRE seule
# laisse passer une phrase de passe en mots ordinaires
# (« correcthorsebatterystaple » : 3,36 bits/caractère, sous tout seuil
# raisonnable) alors qu'elle vaut 84 bits au total — un vrai secret. On exige
# donc un plancher par caractère, qui écarte la répétition pure, ET un total
# suffisant, qui attrape les valeurs longues à alphabet réduit.
MIN_ENTROPY_BITS = 2.6
MIN_TOTAL_ENTROPY_BITS = 60.0


def shannon_bits_per_char(value: str) -> float:
    if not value:
        return 0.0
    counts = Counter(value)
    total = len(value)
    return -sum((n / total) * math.log2(n / total) for n in counts.values())


def load_allowlist() -> dict[str, str]:
    """Exemptions littérales : ``"<chemin>:<code>:<extrait exact>" -> motif``."""
    if not ALLOWLIST_PATH.is_file():
        return {}
    raw = yaml.safe_load(ALLOWLIST_PATH.read_text(encoding="utf-8")) or {}
    entries = raw.get("allow") or []
    allowed: dict[str, str] = {}
    for entry in entries:
        missing = [k for k in ("path", "code", "match", "reason") if not entry.get(k)]
        if missing:
            raise SystemExit(
                f"manifests/secret-allowlist.yaml : entrée incomplète, champs manquants {missing}"
            )
        allowed[f"{entry['path']}:{entry['code']}:{entry['match']}"] = str(entry["reason"])
    return allowed


def declared_matches() -> set[str]:
    """Les seules valeurs que l'allowlist a le droit de contenir.

    L'allowlist cite forcément les extraits qu'elle exempte : les scanner
    reviendrait à s'auto-signaler. Le fichier ENTIER était donc dispensé du
    balayage — et un audit a montré que deux jetons de forme créditable placés
    dans un COMMENTAIRE y passaient inaperçus, alors que le même texte dans
    `NOW.md` était détecté. La porte affirmait pourtant « on ne peut donc pas y
    garer un secret ».

    L'exemption porte désormais sur les valeurs des champs ``match``, et sur
    elles seules. Tout le reste du fichier — commentaires, champs ``reason``,
    clés inconnues — est balayé comme n'importe quel fichier suivi.
    """
    if not ALLOWLIST_PATH.is_file():
        return set()
    raw = yaml.safe_load(ALLOWLIST_PATH.read_text(encoding="utf-8")) or {}
    return {str(entry["match"]) for entry in (raw.get("allow") or []) if entry.get("match")}


def tracked_files() -> list[Path]:
    out = subprocess.run(  # noqa: S603 (argv littéral, sans shell)
        ["git", "-C", str(REPO_ROOT), "ls-files", "-z"],  # noqa: S607 (git résolu par PATH, argv littéral)
        check=True,
        capture_output=True,
    ).stdout
    return [REPO_ROOT / name for name in out.decode("utf-8").split("\0") if name]


class Finding(NamedTuple):
    path: str
    line: int
    code: str
    label: str
    match: str

    def key(self) -> str:
        return f"{self.path}:{self.code}:{self.match}"

    def render(self) -> str:
        # L'extrait n'est JAMAIS affiché : seul son empreinte tronquée l'est,
        # afin qu'un journal de CI ne publie pas le secret qu'il dénonce.
        import hashlib

        digest = hashlib.sha256(self.match.encode("utf-8")).hexdigest()[:12]
        return f"{self.path}:{self.line}: {self.code} ({self.label}) — empreinte {digest}"


# Découpage des lignes très longues. On ne tronque PAS : une ligne d'un seul
# tenant (JSON minifié, artefact généré) est exactement l'endroit où un secret
# passerait inaperçu. Les tranches se chevauchent pour qu'aucun motif ne soit
# coupé en deux à la frontière.
_MAX_LINE = 4000
_OVERLAP = 400


# Une valeur NON quotée n'est une donnée littérale que dans un format de
# configuration. Dans un fichier de code (`.py`, `.ts`, `.tsx`…),
# `token = build_session_token()` est une EXPRESSION, pas un secret : y
# appliquer la même règle produit des dizaines de faux positifs et rend la
# porte inutilisable. La valeur QUOTÉE, elle, est examinée partout.
_CONFIG_SUFFIXES = frozenset(
    {
        ".yaml",
        ".yml",
        ".env",
        ".toml",
        ".ini",
        ".cfg",
        ".conf",
        ".properties",
        ".sh",
        ".bash",
        # La documentation est le 2e format du dépôt (183 fichiers) et elle
        # contient des commandes à copier-coller : `export DB_PASSWORD=…`,
        # `PGPASSWORD=… pg_dump …`. Une valeur non quotée y est bien une
        # DONNÉE, pas une expression — c'est même exactement là qu'un secret
        # se glisse par inadvertance, en recopiant une session réelle.
        ".md",
        # Fichiers de build sans extension ou à extension propre : mêmes
        # affectations littérales.
        ".dockerfile",
        ".mk",
    }
)

#: Noms de fichiers SANS extension dont le contenu est de la configuration.
_CONFIG_FILENAMES = frozenset({"Makefile", "Dockerfile", "Procfile", ".env"})


def _bare_values_are_data(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    if name.startswith(".env"):
        return True
    if name in _CONFIG_FILENAMES or name.startswith("Dockerfile"):
        return True
    return any(name.endswith(suffix) for suffix in _CONFIG_SUFFIXES)


def _is_yaml(path: str) -> bool:
    return path.rsplit("/", 1)[-1].lower().endswith((".yaml", ".yml"))


def _high_entropy(value: str) -> bool:
    per_char = shannon_bits_per_char(value)
    return per_char >= MIN_ENTROPY_BITS and per_char * len(value) >= MIN_TOTAL_ENTROPY_BITS


def _yaml_block_scalar_finding(path: str, lines: list[str], index: int) -> Finding | None:
    """Valeur d'un scalaire bloc YAML ouvert à `lines[index]`, si elle existe.

    Le corps est constitué des lignes suivantes strictement PLUS indentées que
    la clé (les lignes vides ne ferment pas le bloc). La reconstitution est
    textuelle : aucun analyseur YAML n'est chargé, donc aucun code tiers ne
    lit un fichier potentiellement hostile pendant un contrôle de sécurité.
    """
    header = BLOCK_SCALAR_HEADER.match(lines[index])
    if header is None:
        return None
    name = header.group("name")
    if NAME_IS_A_DIGEST.search(name):
        return None
    indent = len(header.group("indent"))
    body: list[str] = []
    for line in lines[index + 1 :]:
        if not line.strip():
            body.append("")
            continue
        if len(line) - len(line.lstrip(" ")) <= indent:
            break
        body.append(line.strip())
    value = "\n".join(body).strip()
    # Même règle sensible à la valeur que pour une affectation sur une ligne :
    # le nom seul n'exempte que les empreintes ; un nom d'emplacement n'exempte
    # que si la valeur en est réellement un.
    if name_is_not_the_secret(name, value):
        return None
    if not value or PLACEHOLDER.match(value) or not _high_entropy(value):
        return None
    return Finding(
        path,
        index + 1,
        "HIGH_ENTROPY_ASSIGNMENT",
        f"valeur à forte entropie affectée à « {name} » (scalaire bloc YAML)",
        value,
    )


#: Mots qui, dans une valeur, annoncent un gabarit plutôt qu'une donnée.
_MARKER_WORDS = re.compile(
    r"(?i)(example|exemple|placeholder|change[_-]?me|redacted|fictif|dummy|"
    r"fake|sample|synthetic|todo)"
)


def _entropy_survives_the_marker(value: str) -> bool:
    """Le marqueur retiré, ce qui reste porte-t-il encore un secret ?

    Un gabarit honnête (`api-key-example`, `CHANGE_ME`) n'a rien derrière son
    marqueur. Un secret décoré (`9f3b7d1c8a2e4056b1d9c-synthetic`) garde toute
    son entropie une fois le mot retiré — c'est ce résidu qui est mesuré.
    """
    residue = _MARKER_WORDS.sub("", value).strip(" _-.:/")
    if len(residue) < 16:
        return False
    per_char = shannon_bits_per_char(residue)
    return per_char >= MIN_ENTROPY_BITS and per_char * len(residue) >= MIN_TOTAL_ENTROPY_BITS


def _scan_line(path: str, number: int, line: str) -> Iterable[Finding]:
    for rule in RULES:
        for found in rule.pattern.finditer(line):
            captured = found.group(1) if found.groups() else found.group(0)
            if found.groups() and PLACEHOLDER.match(captured.strip()):
                # Valeur capturée manifestement fictive (``CHANGE_ME``,
                # ``${VAR}``…) : la forme du secret est là, la donnée non.
                continue
            yield Finding(path, number, rule.code, rule.label, captured)
    for found in UNTERMINATED_ASSIGNMENT.finditer(line):
        opened = found.group("open").strip()
        if name_is_not_the_secret(found.group("name"), opened):
            continue
        per_char = shannon_bits_per_char(opened)
        if per_char >= MIN_ENTROPY_BITS and per_char * len(opened) >= MIN_TOTAL_ENTROPY_BITS:
            yield Finding(
                path,
                number,
                "HIGH_ENTROPY_ASSIGNMENT",
                f"valeur à forte entropie affectée à « {found.group('name')} » "
                "(guillemet fermant hors de la tranche examinée)",
                opened,
            )
    for found in ASSIGNMENT.finditer(line):
        bare = found.group("bare")
        if bare is not None and not _bare_values_are_data(path):
            continue
        value = (found.group("quoted") or bare or "").strip()
        if name_is_not_the_secret(found.group("name"), value):
            continue
        if PLACEHOLDER.match(value) and not (
            _MARKER_WORDS.search(value) and _entropy_survives_the_marker(value)
        ):
            # Un vrai secret décoré d'un suffixe de marqueur reste un secret :
            # `…b1d9c-synthetic` matchait PLACEHOLDER et passait, alors que
            # « synthetic » est le mot le plus courant du dépôt. On retire le
            # marqueur et on remesure : si ce qui reste porte encore l'entropie
            # d'un secret, ce n'était pas un gabarit.
            continue
        if not _high_entropy(value):
            continue
        yield Finding(
            path,
            number,
            "HIGH_ENTROPY_ASSIGNMENT",
            f"valeur à forte entropie affectée à « {found.group('name')} »",
            value,
        )


def scan_text(path: str, text: str) -> Iterable[Finding]:
    seen: set[tuple[int, str, str]] = set()
    lines = text.splitlines()
    is_yaml = _is_yaml(path)
    for index, line in enumerate(lines):
        number = index + 1
        if is_yaml:
            block = _yaml_block_scalar_finding(path, lines, index)
            if block is not None:
                marker = (block.line, block.code, block.match)
                if marker not in seen:
                    seen.add(marker)
                    yield block
        if len(line) > _MAX_LINE:
            chunks = [
                line[start : start + _MAX_LINE]
                for start in range(0, len(line), _MAX_LINE - _OVERLAP)
            ]
        else:
            chunks = [line]
        for chunk in chunks:
            for finding in _scan_line(path, number, chunk):
                # Le recouvrement peut faire voir deux fois le même motif.
                marker = (finding.line, finding.code, finding.match)
                if marker in seen:
                    continue
                seen.add(marker)
                yield finding


def main() -> int:
    allowlist = load_allowlist()
    citations = declared_matches()
    used: set[str] = set()
    findings: list[Finding] = []

    for absolute in tracked_files():
        if not absolute.is_file():
            continue
        relative = absolute.relative_to(REPO_ROOT).as_posix()
        if absolute.suffix.lower() in BINARY_SUFFIXES:
            continue
        if absolute.stat().st_size > MAX_BYTES:
            continue
        try:
            text = absolute.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue  # non textuel : aucune règle n'est applicable
        for finding in scan_text(relative, text):
            if finding.key() in allowlist:
                used.add(finding.key())
                continue
            if absolute == ALLOWLIST_PATH and finding.match in citations:
                # L'allowlist a le droit de contenir les extraits qu'elle
                # exempte, et RIEN d'autre. Cette occurrence-ci ne consomme
                # aucune exemption : `used` ne la compte pas, donc une entrée
                # dont la valeur n'apparaît dans aucun VRAI fichier reste
                # rejetée comme exemption morte.
                continue
            findings.append(finding)

    stale = sorted(set(allowlist) - used)
    if stale:
        print("Exemptions inutilisées dans manifests/secret-allowlist.yaml :", file=sys.stderr)
        for key in stale:
            print(f"  - {key}", file=sys.stderr)
        print(
            "Une exemption sans occurrence est une dette morte : la supprimer.",
            file=sys.stderr,
        )
        return 1

    if findings:
        print("SECRETS VRAISEMBLABLES DÉTECTÉS :", file=sys.stderr)
        for finding in findings:
            print(f"  - {finding.render()}", file=sys.stderr)
        print(
            "\nAucune valeur n'est reproduite ici. Vérifier, RÉVOQUER si réel,"
            " puis purger l'historique avant toute publication.",
            file=sys.stderr,
        )
        return 1

    print(f"Aucun secret détecté ({len(tracked_files())} fichiers suivis).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
