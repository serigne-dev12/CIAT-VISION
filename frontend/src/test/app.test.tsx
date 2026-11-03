/** Tests du frontend : mise en forme, permissions, composants et connexion (API simulée). */
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AuthProvider } from "../auth/AuthContext";
import KpiCard from "../components/KpiCard";
import { Pagination, StatusBadge } from "../components/ui";
import { EMPTY_FILTERS, filtersToBody, filtersToParams, periodBounds } from "../components/DataContext";
import { fmtFCFA, fmtKpi, fmtTaux, peut } from "../lib/format";
import LoginPage from "../pages/LoginPage";

afterEach(() => { vi.restoreAllMocks(); sessionStorage.clear(); });

describe("mise en forme française", () => {
  it("formate montants, taux et valeurs non calculables", () => {
    expect(fmtFCFA(12500000).replace(/\s/g, " ")).toBe("12 500 000 FCFA");
    expect(fmtTaux(0.4453)).toBe("44,5 %");
    expect(fmtTaux(null)).toBe("—");
    expect(fmtKpi(null, "rate")).toBe("—");
    expect(fmtKpi(64.7, "percent")).toBe("64,7 %");
  });
});

describe("matrice des droits (affichage)", () => {
  it("n'autorise la modification qu'aux administrateurs et coordonnateurs", () => {
    expect(peut("admin", "modifier")).toBe(true);
    expect(peut("coordinator", "modifier")).toBe(true);
    expect(peut("analyst", "modifier")).toBe(false);
    expect(peut("coordinator", "administrer")).toBe(false);
    expect(peut(undefined, "importer")).toBe(false);
  });
});

describe("composants", () => {
  it("la carte KPI affiche la valeur calculée et sa définition dans une infobulle", async () => {
    render(<KpiCard kpi={{ key: "selection_rate", label: "Taux de sélection", unit: "rate", value: 0.5, definition: "Acceptées ÷ décidées." }} />);
    expect(screen.getByText("50,0 %")).toBeInTheDocument();
    const bouton = screen.getByRole("button", { name: /Acceptées ÷ décidées/ });  // définition accessible aux lecteurs d'écran
    expect(screen.queryByRole("tooltip")).not.toBeInTheDocument();
    await userEvent.click(bouton);
    expect(screen.getByRole("tooltip")).toHaveTextContent("Acceptées ÷ décidées.");
  });

  it("la pastille de statut affiche le libellé", () => {
    render(<StatusBadge status="En incubation" />);
    expect(screen.getByText("En incubation")).toBeInTheDocument();
  });

  it("la pagination désactive les boutons aux extrémités", async () => {
    const onChange = vi.fn();
    render(<Pagination page={1} pageSize={20} total={45} onChange={onChange} />);
    expect(screen.getByText("1 / 3")).toBeInTheDocument();
    expect(screen.getByLabelText("Page précédente")).toBeDisabled();
    await userEvent.click(screen.getByLabelText("Page suivante"));
    expect(onChange).toHaveBeenCalledWith(2);
  });
});

describe("connexion", () => {
  const afficher = () => render(<MemoryRouter><AuthProvider><LoginPage /></AuthProvider></MemoryRouter>);

  it("exige identifiant et mot de passe", async () => {
    afficher();
    await userEvent.click(screen.getByRole("button", { name: /se connecter/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Saisissez votre identifiant");
  });

  it("affiche le message d'erreur renvoyé par l'API", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ detail: "Identifiant ou mot de passe incorrect." }), { status: 401 }));
    afficher();
    await userEvent.type(screen.getByLabelText("Identifiant"), "admin");
    await userEvent.type(screen.getByLabelText("Mot de passe"), "faux");
    await userEvent.click(screen.getByRole("button", { name: /se connecter/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Identifiant ou mot de passe incorrect.");
  });

  it("enregistre le jeton après une connexion réussie", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({
      access_token: "jeton-test", expires_at: new Date(Date.now() + 3600e3).toISOString(),
      user: { id: 1, username: "admin", full_name: "Admin", email: null, role: "admin", is_active: true },
    }), { status: 200 }));
    afficher();
    await userEvent.type(screen.getByLabelText("Identifiant"), "admin");
    await userEvent.type(screen.getByLabelText("Mot de passe"), "Admin@2026");
    await userEvent.click(screen.getByRole("button", { name: /se connecter/i }));
    await waitFor(() => expect(sessionStorage.getItem("ciat_vision_token")).toBe("jeton-test"));
  });
});

describe("filtres V2", () => {
  it("calcule les périodes prédéfinies", () => {
    const sept = periodBounds("7d", { start: "", end: "" });
    const jours = (new Date(sept.end).getTime() - new Date(sept.start).getTime()) / 86400000;
    expect(jours).toBe(6);  // 7 jours, aujourd'hui inclus
    const an = new Date().getFullYear();
    expect(periodBounds("year", { start: "", end: "" })).toEqual({ start: `${an}-01-01`, end: `${an}-12-31` });
    expect(periodBounds("custom", { start: "2025-02-01", end: "2025-03-01" })).toEqual({ start: "2025-02-01", end: "2025-03-01" });
    expect(periodBounds("", { start: "x", end: "y" })).toEqual({ start: "", end: "" });
  });

  it("convertit les filtres en paramètres de l'API (GET et JSON)", () => {
    const f = { ...EMPTY_FILTERS, period: "custom" as const, start_date: "2025-01-01", end_date: "2025-06-30", cohort_id: "3",
      responsible_id: "2", performance: "Faible", funding_level: "Non financé" };
    expect(filtersToParams(f)).toEqual({ start_date: "2025-01-01", end_date: "2025-06-30", cohort_id: "3", responsible_id: "2",
      performance: "Faible", funding_level: "Non financé" });
    const b = filtersToBody(f);
    expect(b.cohort_ids).toEqual([3]);
    expect(b.responsible_ids).toEqual([2]);
    expect(b.performance_levels).toEqual(["Faible"]);
    expect(b.domain_ids).toEqual([]);
    expect(filtersToParams(EMPTY_FILTERS)).toEqual({});
  });
});
