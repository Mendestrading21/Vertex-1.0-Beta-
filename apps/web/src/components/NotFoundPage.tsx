import { Link } from 'react-router-dom';

import { DEFAULT_PATH } from '../app/pages.ts';

/** Route inconnue : état explicite, jamais une redirection silencieuse vers une autre donnée. */
export function NotFoundPage() {
  return (
    <article className="vx-not-found" aria-labelledby="vx-not-found-title">
      <h1 id="vx-not-found-title">Page introuvable</h1>
      <p className="vx-not-installed-question">
        Cette adresse ne correspond à aucune page de Vertex.
      </p>
      <p className="vx-not-installed-note">
        <Link to={DEFAULT_PATH}>Revenir à la page Aujourd'hui</Link>
      </p>
    </article>
  );
}
