import { useState, useSyncExternalStore } from 'react';
import { useNavigate } from 'react-router-dom';

import {
  isApiError,
  postLoginOptions,
  postLoginVerify,
  postLogout,
  postRegisterOptions,
  postRegisterVerify,
  sessionStore,
} from '../api/client.ts';

/**
 * Page Accès — enrôlement/ouverture de session passkey MINIMAL.
 *
 * Deux parcours seulement, sans mot de passe et sans repli :
 * - « Créer la passkey (premier démarrage) » : register/options →
 *   `navigator.credentials.create` → register/verify, puis ouverture de
 *   session par le parcours login (le serveur n'ouvre pas de session à
 *   l'enrôlement) ;
 * - « Se connecter » : login/options → `navigator.credentials.get` →
 *   login/verify (cookies de session posés par le serveur).
 *
 * Toute erreur affiche le même message générique : le serveur répond un 401
 * identique quelle que soit la cause (fail-closed) et l'interface n'invente
 * aucune cause détaillée.
 */

type Busy = 'none' | 'register' | 'login' | 'logout';

const GENERIC_FAILURE =
  "Échec de l'authentification. Le serveur répond volontairement sans détail (401 générique) ; " +
  'vérifiez que l’API locale tourne et que la passkey existe sur cet appareil.';

function webauthnJsonSupported(): boolean {
  return (
    typeof PublicKeyCredential !== 'undefined' &&
    'parseCreationOptionsFromJSON' in PublicKeyCredential &&
    'parseRequestOptionsFromJSON' in PublicKeyCredential
  );
}

async function runLoginCeremony(): Promise<void> {
  const ceremony = await postLoginOptions();
  const publicKey = PublicKeyCredential.parseRequestOptionsFromJSON(
    ceremony.options as unknown as PublicKeyCredentialRequestOptionsJSON,
  );
  const credential = await navigator.credentials.get({ publicKey });
  if (!(credential instanceof PublicKeyCredential)) {
    throw new Error('WebAuthn assertion unavailable');
  }
  await postLoginVerify({
    flow_id: ceremony.flow_id,
    credential: credential.toJSON() as unknown as Record<string, unknown>,
  });
}

async function runRegisterCeremony(): Promise<void> {
  const ceremony = await postRegisterOptions();
  const publicKey = PublicKeyCredential.parseCreationOptionsFromJSON(
    ceremony.options as unknown as PublicKeyCredentialCreationOptionsJSON,
  );
  const credential = await navigator.credentials.create({ publicKey });
  if (!(credential instanceof PublicKeyCredential)) {
    throw new Error('WebAuthn attestation unavailable');
  }
  await postRegisterVerify({
    flow_id: ceremony.flow_id,
    label: 'Passkey locale',
    credential: credential.toJSON() as unknown as Record<string, unknown>,
  });
}

export function AuthPage() {
  const navigate = useNavigate();
  const session = useSyncExternalStore(sessionStore.subscribe, sessionStore.getState);
  const [busy, setBusy] = useState<Busy>('none');
  const [message, setMessage] = useState<string | null>(null);

  const supported = webauthnJsonSupported();

  async function guard(kind: Busy, action: () => Promise<void>): Promise<void> {
    setBusy(kind);
    setMessage(null);
    try {
      await action();
    } catch (error) {
      if (isApiError(error) && error.kind === 'NETWORK') {
        setMessage("L'API locale est injoignable (hors ligne). Aucune session ouverte.");
      } else {
        setMessage(GENERIC_FAILURE);
      }
    } finally {
      setBusy('none');
    }
  }

  return (
    <article className="vx-page vx-auth" aria-labelledby="vx-page-title-auth">
      <div className="vx-page-header">
        <h1 id="vx-page-title-auth">Accès</h1>
        <p className="vx-page-question">
          Ouvrir une session locale par passkey — aucun mot de passe, aucun repli.
        </p>
      </div>

      {!supported ? (
        <p className="vx-auth-unsupported" role="alert">
          Ce navigateur n'expose pas les API WebAuthn JSON requises
          (PublicKeyCredential.parseCreationOptionsFromJSON). Aucune alternative n'est proposée :
          l'accès exige une passkey.
        </p>
      ) : null}

      <div className="vx-auth-actions">
        <button
          type="button"
          disabled={!supported || busy !== 'none'}
          onClick={() =>
            void guard('register', async () => {
              await runRegisterCeremony();
              // L'enrôlement n'ouvre pas de session côté serveur : on enchaîne
              // la cérémonie d'authentification réelle.
              await runLoginCeremony();
              setMessage('Passkey créée et session ouverte.');
              void navigate('/today');
            })
          }
        >
          {busy === 'register' ? 'Création en cours…' : 'Créer la passkey (premier démarrage)'}
        </button>
        <button
          type="button"
          disabled={!supported || busy !== 'none'}
          onClick={() =>
            void guard('login', async () => {
              await runLoginCeremony();
              setMessage('Session ouverte.');
              void navigate('/today');
            })
          }
        >
          {busy === 'login' ? 'Connexion en cours…' : 'Se connecter'}
        </button>
        {session === 'authenticated' ? (
          <button
            type="button"
            disabled={busy !== 'none'}
            onClick={() =>
              void guard('logout', async () => {
                await postLogout();
                setMessage('Session fermée.');
              })
            }
          >
            {busy === 'logout' ? 'Fermeture…' : 'Se déconnecter'}
          </button>
        ) : null}
      </div>

      {message !== null ? (
        <p className="vx-auth-message" role="status">
          {message}
        </p>
      ) : null}

      <p className="vx-auth-note">
        Règle serveur : la toute première passkey s'enregistre librement ; dès qu'une passkey
        existe, en ajouter une nouvelle exige une session déjà ouverte. Les cookies de session
        (8 h maximum) restent sur la boucle locale.
      </p>
    </article>
  );
}
