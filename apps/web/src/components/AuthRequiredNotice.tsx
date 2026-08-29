import { Link } from 'react-router-dom';

/**
 * État dédié « session requise » — honnête et actionnable.
 * Le serveur a répondu son 401 générique (code AUTH_REQUIRED) : aucune cause
 * détaillée n'existe côté client et aucune n'est inventée ici.
 */
export function AuthRequiredNotice() {
  return (
    <div className="vx-auth-required" role="status" data-state="auth-required">
      <strong>Session requise</strong>
      <p>
        L'API locale a refusé l'accès (réponse générique 401, code AUTH_REQUIRED). Cette page
        n'affiche aucune donnée sans session passkey valide.
      </p>
      <p>
        Ouvrez la page <Link to="/auth">Accès</Link> : au premier démarrage elle crée la première
        passkey (WebAuthn, cérémonie native du navigateur) ; ensuite elle sert à ouvrir une
        session. Aucun mot de passe n'existe et aucun contournement n'est prévu.
      </p>
    </div>
  );
}
