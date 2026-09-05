import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';

import { FreshnessBadge, formatAge, formatBudget, policyProps } from './FreshnessBadge.tsx';

afterEach(() => {
  vi.restoreAllMocks();
});

describe('formatAge — formatage déterministe depuis les props', () => {
  it('distingue âge inconnu (null) et âge invalide (négatif, NaN, infini)', () => {
    expect(formatAge(null)).toBe('âge inconnu');
    expect(formatAge(-1)).toBe('âge invalide');
    expect(formatAge(Number.NaN)).toBe('âge invalide');
    expect(formatAge(Number.POSITIVE_INFINITY)).toBe('âge invalide');
  });

  it('formate secondes, minutes, heures et jours', () => {
    expect(formatAge(0)).toBe('il y a 0 s');
    expect(formatAge(59)).toBe('il y a 59 s');
    expect(formatAge(60)).toBe('il y a 1 min');
    expect(formatAge(3599)).toBe('il y a 59 min');
    expect(formatAge(3600)).toBe('il y a 1 h');
    expect(formatAge(86399)).toBe('il y a 23 h');
    expect(formatAge(86400)).toBe('il y a 1 j');
    expect(formatAge(172800)).toBe('il y a 2 j');
  });
});

describe('FreshnessBadge', () => {
  it("affiche l'âge fourni par props avec la source", () => {
    render(<FreshnessBadge ageSeconds={125} sourceLabel="IBKR différé" />);
    expect(screen.getByText('il y a 2 min')).toBeDefined();
    expect(screen.getByText(/IBKR différé/)).toBeDefined();
  });

  it("affiche « âge inconnu » quand l'âge est null", () => {
    render(<FreshnessBadge ageSeconds={null} />);
    expect(screen.getByText('âge inconnu')).toBeDefined();
  });

  it("ne lit jamais l'horloge du navigateur", () => {
    const nowSpy = vi.spyOn(Date, 'now');
    render(<FreshnessBadge ageSeconds={42} sourceLabel="test" />);
    expect(nowSpy).not.toHaveBeenCalled();
  });
});

describe("L'échelle SERVIE contre laquelle l'âge est jugé", () => {
  /*
    « il y a 3 j » ne dit rien tout seul. Trois jours sur une barre quotidienne
    de séance fermée, c'est normal ; trois jours sur une cotation, c'est une
    donnée morte. Le serveur publie l'échelle qui tranche ; l'interface ne la
    lisait pas.
  */
  it("affiche le budget SERVI à côté de l'âge", () => {
    render(<FreshnessBadge ageSeconds={259_200} budgetSeconds={86_400} />);
    expect(screen.getByText('il y a 3 j')).toBeTruthy();
    expect(screen.getByText('budget 1 j')).toBeTruthy();
  });

  it("porte le nom et la version de la politique sans encombrer la ligne", () => {
    render(
      <FreshnessBadge
        ageSeconds={120}
        budgetSeconds={3600}
        policyKind="daily_bar"
        policyVersion="2"
      />,
    );
    const budget = screen.getByText('budget 1 h');
    expect(budget.getAttribute('title')).toBe('budget 1 h · daily_bar · politique 2');
  });

  it("ne dit RIEN quand la politique n'est pas publiée", () => {
    // Une famille sans TTL au registre publie `null` (matrice de capacités).
    // Un budget absent n'est pas un budget infini, et surtout pas un défaut.
    render(<FreshnessBadge ageSeconds={120} budgetSeconds={null} />);
    expect(screen.queryByText(/budget/)).toBeNull();
  });

  it("tait un budget nul plutôt que de faire lire toute donnée comme périmée", () => {
    // Le serveur refuse un budget nul à la frontière — « la forme qu'une
    // absence prendrait si elle était convertie en zéro ». S'il arrivait
    // quand même, l'afficher rendrait TOUT périmé.
    expect(formatBudget(0)).toBeNull();
    expect(formatBudget(-1)).toBeNull();
    expect(formatBudget(Number.NaN)).toBeNull();
    expect(formatBudget(null)).toBeNull();
    expect(formatBudget(undefined)).toBeNull();
  });

  it('formate le budget comme une DURÉE, jamais comme un instant', () => {
    // « budget 1 j », pas « il y a 1 j » : les deux nombres sont du même
    // ordre, c'est justement pourquoi ils doivent se lire différemment.
    expect(formatBudget(86_400)).toBe('budget 1 j');
    expect(formatBudget(90)).toBe('budget 1 min');
    expect(formatBudget(45)).toBe('budget 45 s');
  });
});

describe('policyProps — un seul endroit connaît les noms du contrat', () => {
  it('rend un objet VIDE sur une politique absente', () => {
    // Vide, et non `{budgetSeconds: null}` : les props ne sont pas posées, donc
    // rien ne peut confondre « non publié » avec « budget nul ».
    expect(policyProps(null)).toEqual({});
    expect(policyProps(undefined)).toEqual({});
  });

  it('transpose les trois champs SERVIS', () => {
    expect(policyProps({ budget_seconds: 3600, kind: 'daily_bar', version: '2' })).toEqual({
      budgetSeconds: 3600,
      policyKind: 'daily_bar',
      policyVersion: '2',
    });
  });
});
