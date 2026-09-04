import usePreferences from '../../hooks/usePreferences';
import './About.css';

const missions = [
  { fr: 'Élaborer et coordonner un plan présidentiel de salubrité et d’assainissement pour Kinshasa.', en: 'Develop and coordinate a presidential sanitation and public cleanliness plan for Kinshasa.' },
  { fr: 'Identifier les points critiques d’insalubrité et organiser leur traitement et leur suivi.', en: 'Identify critical sanitation hotspots and organize their treatment and monitoring.' },
  { fr: 'Coordonner la collecte, le transfert, le traitement et la valorisation des déchets.', en: 'Coordinate waste collection, transfer, treatment and recovery.' },
  { fr: 'Assurer le curage des ouvrages de drainage prioritaires, notamment pour lutter contre les problèmes liés aux eaux et aux caniveaux.', en: 'Clear priority drainage structures, particularly to address problems involving water and drainage channels.' },
  { fr: 'Renforcer la discipline urbaine et l’hygiène publique, avec des mesures de civisme environnemental.', en: 'Strengthen urban discipline and public hygiene through environmental responsibility measures.' },
  { fr: 'Coordonner les opérations sur le terrain avec les différents services de l’État et de la Ville.', en: 'Coordinate field operations with the various national and city government departments.' },
  { fr: 'Sensibiliser et mobiliser la population pour maintenir les quartiers propres.', en: 'Raise awareness and mobilize residents to keep neighborhoods clean.' },
  { fr: 'Proposer des mesures durables pour améliorer le cadre de vie à Kinshasa.', en: 'Propose sustainable measures to improve living conditions in Kinshasa.' },
];

export default function About() {
  const { tr } = usePreferences();

  return (
    <main className="about-page">
      <article className="about-document">
        <header className="about-heading">
          <p className="about-kicker">{tr('À propos', 'About us')}</p>
          <h1>{tr(
            'Task Force Présidentielle de la Salubrité et de l’Assainissement de la Ville de Kinshasa',
            'Presidential Task Force for Sanitation and Public Cleanliness in the City of Kinshasa',
          )}</h1>
        </header>
        <section className="about-introduction">
          <h2>{tr('Ses principales missions sont :', 'Its principal missions are:')}</h2>
          <ul className="about-missions">
            {missions.map((mission) => <li key={mission.fr}>{tr(mission.fr, mission.en)}</li>)}
          </ul>
        </section>
      </article>
    </main>
  );
}
