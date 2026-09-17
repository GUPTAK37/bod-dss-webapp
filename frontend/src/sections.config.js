// Declarative section registry — mirrors the block in bod_app/layouts/bod.py:642-707.

export const SECTIONS = [
  {
    id: 's1',
    title: '% Episodes With Follow-up Visits',
    chartHeight: 300,
    legend: [
      { label: 'Follow-Up Visit', color: '#2AA198' },
      { label: 'No Follow-Up Visit of Interest', color: '#B0B0B0' },
    ],
  },
  {
    id: 's2',
    title: '% Episodes With Follow-up Visits Across Treated and Untreated Cohort',
    chartHeight: 300,
    legend: [
      { label: 'Follow-Up Visit', color: '#2AA198' },
      { label: 'No Follow-Up Visit of Interest', color: '#B0B0B0' },
    ],
  },
  {
    id: 's3',
    title: 'Quarterly % Episodes With Follow-up Visits Across Treated and Untreated Cohort',
    chartHeight: 340,
    legend: [
      { label: 'Follow-Up Visit', color: '#2AA198' },
      { label: 'No Follow-Up Visit of Interest', color: '#B0B0B0' },
    ],
  },
  {
    id: 's4',
    title: 'Average # Follow-up Visits Per Total Episodes',
    chartHeight: 320,
    legend: [
      { label: 'Treated', color: '#531679' },
      { label: 'Untreated', color: '#ed7239' },
    ],
  },
  {
    id: 's5',
    title: 'Characterizing Follow-up Visits',
    chartHeight: 320,
    legend: visitMixLegend(),
  },
  {
    id: 's6',
    title: 'Follow-up Visits across Treated and Untreated Cohort',
    chartHeight: 320,
    legend: visitMixLegend(),
  },
  {
    id: 's7',
    title: 'Quarterly Follow-up Visits Across Treated and Untreated Cohort',
    chartHeight: 340,
    legend: visitMixLegend(),
  },
  {
    id: 's8',
    title: '#Follow-Up Visits Across High Risk Conditions',
    chartHeight: 340,
    localFilters: 's8',
  },
  {
    id: 's9',
    title: '#Follow-Up Visits Across High Risk Conditions and Treated and Untreated Cohort',
    chartHeight: 340,
    legend: [
      { label: 'Treated', color: '#531679' },
      { label: 'Untreated', color: '#ed7239' },
    ],
  },
  {
    id: 's10',
    title: 'COVID-19 Initial Diagnosis/Treatment Location',
    chartHeight: 300,
    localFilters: 's10',
    legend: [
      ...visitMixLegend(),
      { label: 'OTHERS', color: '#ba9789' },
      { label: 'PHARMACY', color: '#b0a983' },
    ],
  },
];

function visitMixLegend() {
  return [
    { label: 'HOSPITALIZATION', color: '#97cfd0' },
    { label: 'ED VISIT', color: '#466db0' },
    { label: 'UC VISIT', color: '#b07aa1' },
    { label: 'LTAC/SNF VISIT', color: '#e15759' },
    { label: 'OFFICE VISIT', color: '#59a14f' },
    { label: 'TELEHEALTH VISIT', color: '#edc948' },
  ];
}
