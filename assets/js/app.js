const DATA_URL = 'data/debt_dashboard.json';
const charts = {};
let dashboardData;

const COLORS = {
  debt: '#0f6f82',
  net: '#a33f4c',
  short: '#4776a8',
  medium: '#77a15f',
  long: '#d39c3f',
  line: '#1f2937',
  gray: '#8b95a5',
  purple: '#6e5c91',
  teal: '#4e9f9c',
  red: '#c75454',
  green: '#6a9f50',
  orange: '#d08a31'
};

const chartColors = [
  '#0f6f82', '#4776a8', '#77a15f', '#d39c3f', '#a33f4c', '#6e5c91', '#4e9f9c', '#8b95a5'
];

function formatNumber(value, decimals = 0) {
  return new Intl.NumberFormat('it-IT', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  }).format(value);
}

function toSelectedUnit(value) {
  const unit = document.getElementById('unitSelect').value;
  return unit === 'bn' ? value / 1000 : value;
}

function unitLabel() {
  return document.getElementById('unitSelect').value === 'bn' ? 'mld €' : 'mln €';
}

function formatMoney(value, decimals = 1) {
  const unit = document.getElementById('unitSelect')?.value || 'bn';
  if (unit === 'bn') return `${formatNumber(value / 1000, decimals)} mld €`;
  return `${formatNumber(value, 0)} mln €`;
}

function pct(value, total) {
  if (!total) return '—';
  return `${formatNumber((value / total) * 100, 1)}%`;
}

function getFilteredMonthly() {
  const range = document.getElementById('rangeSelect').value;
  const rows = dashboardData.monthly;
  if (range === 'all') return rows;
  return rows.slice(-Number(range));
}

function getFilteredHolders() {
  const range = document.getElementById('rangeSelect').value;
  const rows = dashboardData.holders;
  if (range === 'all') return rows;
  return rows.slice(-Number(range));
}

function destroyChart(id) {
  if (charts[id]) {
    charts[id].destroy();
    delete charts[id];
  }
}

function chartDefaults() {
  Chart.defaults.font.family = 'Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif';
  Chart.defaults.color = '#4b5563';
  Chart.defaults.borderColor = '#d8dde5';
}

function baseOptions(extra = {}) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { position: 'bottom', labels: { boxWidth: 12, boxHeight: 12 } },
      tooltip: {
        callbacks: {
          label: function(context) {
            const label = context.dataset.label || '';
            const raw = context.raw;
            if (context.dataset.yAxisID === 'years') return `${label}: ${formatNumber(raw, 1)} anni`;
            if (context.chart.canvas.id === 'holdersChart') return `${label}: ${formatNumber(raw, 1)}%`;
            return `${label}: ${formatNumber(raw, 1)} ${unitLabel()}`;
          }
        }
      }
    },
    scales: {
      x: { grid: { display: false } },
      y: {
        beginAtZero: false,
        ticks: { callback: value => `${formatNumber(value, 0)}` },
        title: { display: true, text: unitLabel() }
      }
    },
    ...extra
  };
}

function renderMetadata() {
  const meta = dashboardData.metadata;
  document.getElementById('sourceName').textContent = meta.source_name;
  document.getElementById('sourceLink').href = meta.source_url;
  document.getElementById('releaseDate').textContent = `Aggiornamento dati: ${meta.release_date}`;
  document.getElementById('referencePeriod').textContent = `Periodo riferimento: ${meta.reference_period}`;
  document.getElementById('methodologyText').textContent = `${meta.description} Unità originale del dataset: ${meta.unit}.`;

  const notes = document.getElementById('notesList');
  notes.innerHTML = '';
  meta.notes.forEach(note => {
    const li = document.createElement('li');
    li.textContent = note;
    notes.appendChild(li);
  });
}

function renderKpis() {
  const latest = dashboardData.monthly[dashboardData.monthly.length - 1];
  const prev = dashboardData.monthly[dashboardData.monthly.length - 2];
  const delta = latest.debt_total - prev.debt_total;
  const securities = latest.short_term_securities + latest.medium_long_term_securities;
  const securitiesShare = securities / latest.debt_total;

  const kpis = [
    { label: 'Debito lordo', value: formatMoney(latest.debt_total), note: `${latest.label}${latest.provisional ? ' · dato provvisorio' : ''}` },
    { label: 'Debito al netto liquidità', value: formatMoney(latest.debt_net_liquidity), note: `Liquidità Tesoro: ${formatMoney(latest.treasury_liquidity)}` },
    { label: 'Variazione mensile', value: formatMoney(delta), note: `rispetto a ${prev.label}` },
    { label: 'Vita media residua', value: `${formatNumber(latest.avg_residual_life_years, 1)} anni`, note: 'debito delle PA' },
    { label: 'Titoli sul debito', value: `${formatNumber(securitiesShare * 100, 1)}%`, note: `${formatMoney(securities)} in titoli` }
  ];

  const grid = document.getElementById('kpiGrid');
  grid.innerHTML = '';
  kpis.forEach(item => {
    const card = document.createElement('article');
    card.className = 'kpi';
    card.innerHTML = `<div class="kpi-label">${item.label}</div><div class="kpi-value">${item.value}</div><div class="kpi-note">${item.note}</div>`;
    grid.appendChild(card);
  });
}

function renderDebtChart() {
  destroyChart('debtChart');
  const rows = getFilteredMonthly();
  const labels = rows.map(d => d.label);
  charts.debtChart = new Chart(document.getElementById('debtChart'), {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Debito lordo',
          data: rows.map(d => toSelectedUnit(d.debt_total)),
          borderColor: COLORS.debt,
          backgroundColor: COLORS.debt,
          tension: 0.25,
          pointRadius: 3
        },
        {
          label: 'Debito al netto liquidità Tesoro',
          data: rows.map(d => toSelectedUnit(d.debt_net_liquidity)),
          borderColor: COLORS.net,
          backgroundColor: COLORS.net,
          tension: 0.25,
          pointRadius: 3
        }
      ]
    },
    options: baseOptions()
  });
}

function renderInstrumentChart() {
  destroyChart('instrumentChart');
  const latest = dashboardData.monthly[dashboardData.monthly.length - 1];
  const labels = [
    'Monete e depositi',
    'Titoli a breve termine',
    'Titoli a medio-lungo termine',
    'Prestiti IFM',
    'Prestiti istituzioni europee',
    'Altre passività'
  ];
  const values = [
    latest.coins_deposits,
    latest.short_term_securities,
    latest.medium_long_term_securities,
    latest.ifm_loans,
    latest.eu_institutions_loans,
    latest.other_liabilities
  ];
  charts.instrumentChart = new Chart(document.getElementById('instrumentChart'), {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        label: 'Composizione',
        data: values.map(toSelectedUnit),
        backgroundColor: chartColors,
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 12, boxHeight: 12 } },
        tooltip: {
          callbacks: {
            label: ctx => `${ctx.label}: ${formatNumber(ctx.raw, 1)} ${unitLabel()} (${pct(values[ctx.dataIndex], latest.debt_total)})`
          }
        }
      }
    }
  });
}

function renderOriginalMaturityChart() {
  destroyChart('originalMaturityChart');
  const m = dashboardData.original_maturity_latest;
  charts.originalMaturityChart = new Chart(document.getElementById('originalMaturityChart'), {
    type: 'bar',
    data: {
      labels: ['Scadenza originaria'],
      datasets: [
        { label: 'Breve termine', data: [toSelectedUnit(m.short_original_total)], backgroundColor: COLORS.short },
        { label: 'Medio-lungo termine', data: [toSelectedUnit(m.medium_long_original_total)], backgroundColor: COLORS.medium }
      ]
    },
    options: baseOptions({
      scales: {
        x: { stacked: true, grid: { display: false } },
        y: { stacked: true, title: { display: true, text: unitLabel() } }
      }
    })
  });
}

function renderResidualMaturityChart() {
  destroyChart('residualMaturityChart');
  const rows = getFilteredMonthly();
  charts.residualMaturityChart = new Chart(document.getElementById('residualMaturityChart'), {
    data: {
      labels: rows.map(d => d.label),
      datasets: [
        {
          type: 'bar',
          label: 'Fino a 1 anno',
          data: rows.map(d => toSelectedUnit(d.residual_upto_1y)),
          backgroundColor: COLORS.short,
          stack: 'maturity'
        },
        {
          type: 'bar',
          label: 'Tra 1 e 5 anni',
          data: rows.map(d => toSelectedUnit(d.residual_1_5y)),
          backgroundColor: COLORS.medium,
          stack: 'maturity'
        },
        {
          type: 'bar',
          label: 'Oltre 5 anni',
          data: rows.map(d => toSelectedUnit(d.residual_over_5y)),
          backgroundColor: COLORS.long,
          stack: 'maturity'
        },
        {
          type: 'line',
          label: 'Vita media residua',
          data: rows.map(d => d.avg_residual_life_years),
          borderColor: COLORS.line,
          backgroundColor: COLORS.line,
          yAxisID: 'years',
          tension: 0.2,
          pointRadius: 3
        }
      ]
    },
    options: baseOptions({
      scales: {
        x: { stacked: true, grid: { display: false } },
        y: { stacked: true, title: { display: true, text: unitLabel() } },
        years: {
          position: 'right',
          beginAtZero: false,
          grid: { drawOnChartArea: false },
          title: { display: true, text: 'anni' },
          ticks: { callback: value => formatNumber(value, 1) }
        }
      }
    })
  });
}

function renderHoldersChart() {
  destroyChart('holdersChart');
  const rows = getFilteredHolders();
  const labels = rows.map(d => d.label);
  const asShare = key => rows.map(d => (d[key] / d.debt_total) * 100);
  charts.holdersChart = new Chart(document.getElementById('holdersChart'), {
    type: 'bar',
    data: {
      labels,
      datasets: [
        { label: "Banca d'Italia", data: asShare('banca_italia'), backgroundColor: COLORS.short, stack: 'holders' },
        { label: 'Altre IFM residenti', data: asShare('other_mfi_resident'), backgroundColor: COLORS.red, stack: 'holders' },
        { label: 'Altre istituzioni finanziarie residenti', data: asShare('other_resident_financial_institutions'), backgroundColor: COLORS.green, stack: 'holders' },
        { label: 'Altri residenti', data: asShare('other_residents'), backgroundColor: COLORS.purple, stack: 'holders' },
        { label: 'Non residenti', data: asShare('non_residents'), backgroundColor: COLORS.teal, stack: 'holders' }
      ]
    },
    options: baseOptions({
      scales: {
        x: { stacked: true, grid: { display: false } },
        y: {
          stacked: true,
          min: 0,
          max: 100,
          ticks: { callback: value => `${value}%` },
          title: { display: true, text: 'quota sul totale' }
        }
      }
    })
  });
}

function renderFlowChart() {
  destroyChart('flowChart');
  const rows = getFilteredMonthly();
  const labels = rows.map(d => d.label);
  const debtDelta = rows.map((d, i) => {
    const fullIndex = dashboardData.monthly.findIndex(row => row.date === d.date);
    if (fullIndex <= 0) return null;
    return toSelectedUnit(d.debt_total - dashboardData.monthly[fullIndex - 1].debt_total);
  });

  charts.flowChart = new Chart(document.getElementById('flowChart'), {
    data: {
      labels,
      datasets: [
        {
          type: 'bar',
          label: 'Fabbisogno',
          data: rows.map(d => toSelectedUnit(d.borrowing_requirement)),
          backgroundColor: COLORS.red
        },
        {
          type: 'bar',
          label: 'Contributo liquidità Tesoro',
          data: rows.map(d => toSelectedUnit(d.liquidity_change_contribution)),
          backgroundColor: COLORS.green
        },
        {
          type: 'line',
          label: 'Variazione del debito',
          data: debtDelta,
          borderColor: COLORS.debt,
          backgroundColor: COLORS.debt,
          tension: 0.25,
          pointRadius: 3
        }
      ]
    },
    options: baseOptions({
      scales: {
        x: { grid: { display: false } },
        y: { title: { display: true, text: unitLabel() } }
      }
    })
  });
}

function renderLatestTable() {
  const latest = dashboardData.monthly[dashboardData.monthly.length - 1];
  const m = dashboardData.original_maturity_latest;
  const tbody = document.querySelector('#latestTable tbody');
  const securities = latest.short_term_securities + latest.medium_long_term_securities;
  const rows = [
    ['Debito delle Amministrazioni pubbliche', formatNumber(latest.debt_total), `${formatMoney(latest.debt_total)}${latest.provisional ? ' · provvisorio' : ''}`],
    ['Debito al netto disponibilità liquide del Tesoro', formatNumber(latest.debt_net_liquidity), formatMoney(latest.debt_net_liquidity)],
    ['Disponibilità liquide del Tesoro', formatNumber(latest.treasury_liquidity), pct(latest.treasury_liquidity, latest.debt_total)],
    ['Titoli totali', formatNumber(securities), pct(securities, latest.debt_total)],
    ['Titoli a breve termine', formatNumber(latest.short_term_securities), pct(latest.short_term_securities, latest.debt_total)],
    ['Titoli a medio-lungo termine', formatNumber(latest.medium_long_term_securities), pct(latest.medium_long_term_securities, latest.debt_total)],
    ['Debito con vita residua fino a 1 anno', formatNumber(latest.residual_upto_1y), pct(latest.residual_upto_1y, latest.debt_total)],
    ['Debito con vita residua tra 1 e 5 anni', formatNumber(latest.residual_1_5y), pct(latest.residual_1_5y, latest.debt_total)],
    ['Debito con vita residua oltre 5 anni', formatNumber(latest.residual_over_5y), pct(latest.residual_over_5y, latest.debt_total)],
    ['Vita media residua', formatNumber(latest.avg_residual_life_years, 1), 'anni'],
    ['Debito in euro', formatNumber(m.euro_debt), pct(m.euro_debt, m.total_debt)],
    ['Debito in valuta estera', formatNumber(m.foreign_currency_debt), pct(m.foreign_currency_debt, m.total_debt)]
  ];

  tbody.innerHTML = '';
  rows.forEach(row => {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${row[0]}</td><td>${row[1]}</td><td>${row[2]}</td>`;
    tbody.appendChild(tr);
  });
}

function renderAll() {
  renderKpis();
  renderDebtChart();
  renderInstrumentChart();
  renderOriginalMaturityChart();
  renderResidualMaturityChart();
  renderHoldersChart();
  renderFlowChart();
  renderLatestTable();
}

async function init() {
  chartDefaults();
  const response = await fetch(DATA_URL);
  if (!response.ok) throw new Error(`Impossibile caricare ${DATA_URL}`);
  dashboardData = await response.json();
  renderMetadata();
  renderAll();

  document.getElementById('rangeSelect').addEventListener('change', renderAll);
  document.getElementById('unitSelect').addEventListener('change', renderAll);
}

init().catch(error => {
  console.error(error);
  document.body.insertAdjacentHTML('afterbegin', `<div class="container"><div class="panel" style="margin-top: 16px; color: #a33f4c;">Errore nel caricamento della dashboard: ${error.message}</div></div>`);
});
