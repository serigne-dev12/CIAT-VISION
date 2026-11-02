/**
 * Couleurs des graphiques. Une série unique est toujours en marron (l'axe porte l'identité) ;
 * les catégories (statuts, séries) ont une couleur FIXE, identique dans tous les graphiques.
 */
export const BRUN = "#4C311F";
export const BEIGE = "#CA9871";
export const GRILLE = "#EEE8E2";
export const AXE = "#8C8A85";

// Palette catégorielle distinguable par les daltoniens (ordre fixe)
export const SERIES = ["#4C311F", "#CA9871", "#2A78D6", "#1BAF7A", "#6250D6", "#E87BA4", "#EB6834", "#8C8A85"];

export const STATUT_COULEURS: Record<string, string> = {
  "En attente": "#B9B4AE",
  "En évaluation": "#EDA100",
  "Non retenu": "#D9D4CE",
  "Sélectionné": "#CA9871",
  "En incubation": "#2A78D6",
  "En développement": "#6250D6",
  "Prototype réalisé": "#4C311F",
  "Terminé": "#1BAF7A",
  "Suspendu": "#E34948",
};

/** Classes de pastille de statut (texte foncé sur fond clair : contraste AA). */
export const STATUT_BADGE: Record<string, string> = {
  "En attente": "bg-stone-100 text-stone-700",
  "En évaluation": "bg-amber-50 text-amber-800",
  "Non retenu": "bg-stone-100 text-stone-500",
  "Sélectionné": "bg-beige-pale text-profond",
  "En incubation": "bg-blue-50 text-blue-800",
  "En développement": "bg-violet-50 text-violet-800",
  "Prototype réalisé": "bg-[#efe6de] text-brun",
  "Terminé": "bg-emerald-50 text-emerald-800",
  "Suspendu": "bg-red-50 text-red-800",
};
