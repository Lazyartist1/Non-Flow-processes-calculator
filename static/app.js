document.addEventListener("DOMContentLoaded", () => {
  const form = document.getElementById("calc-form");
  const processSelect = document.getElementById("process_type");
  const substanceSelect = document.getElementById("substance");
  const resultsGrid = document.getElementById("results-grid");
  const pvDiv = document.getElementById("pv-plot");
  const tsDiv = document.getElementById("ts-plot");

  const PROCESS_TYPES = [
    "constantVolume",
    "constantPressure",
    "isothermal",
    "adiabatic",
    "polytropic",
  ];

  // populate process types
  PROCESS_TYPES.forEach(p => {
    const opt = document.createElement("option");
    opt.value = p;
    opt.textContent = p;
    processSelect.appendChild(opt);
  });

  // Render process cards (visual selectors). Keep select element for form semantics.
  const processCardsContainer = document.getElementById('process-cards');
  function renderProcessCards() {
    processCardsContainer.innerHTML = '';
    PROCESS_TYPES.forEach(p => {
      const card = document.createElement('div');
      card.className = 'card';
      card.textContent = p;
      card.tabIndex = 0;
      card.onclick = () => {
        // update hidden select and trigger change
        processSelect.value = p;
        processSelect.dispatchEvent(new Event('change'));
        // active state
        Array.from(processCardsContainer.children).forEach(c => c.classList.remove('active'));
        card.classList.add('active');
      };
      card.onkeypress = (e) => { if (e.key === 'Enter' || e.key === ' ') card.onclick(); };
      processCardsContainer.appendChild(card);
    });
    // set initial selection
    processSelect.value = PROCESS_TYPES[0];
    processSelect.dispatchEvent(new Event('change'));
    if (processCardsContainer.firstChild) processCardsContainer.firstChild.classList.add('active');
  }
  renderProcessCards();

  // fetch substances from backend
  fetch('/substances')
    .then(r => r.json())
    .then(list => {
      list.forEach(s => {
        const opt = document.createElement('option');
        opt.value = s.key;
        opt.textContent = s.name;
        substanceSelect.appendChild(opt);
      });
      // render substance cards
      const substanceCardsContainer = document.getElementById('substance-cards');
      substanceCardsContainer.innerHTML = '';
      list.forEach(s => {
        const card = document.createElement('div');
        card.className = 'card';
        card.textContent = s.name;
        card.tabIndex = 0;
        card.onclick = () => {
          substanceSelect.value = s.key;
          // active state
          Array.from(substanceCardsContainer.children).forEach(c => c.classList.remove('active'));
          card.classList.add('active');
        };
        card.onkeypress = (e) => { if (e.key === 'Enter' || e.key === ' ') card.onclick(); };
        substanceCardsContainer.appendChild(card);
      });
      // initial substance selection
      if (list.length > 0) {
        substanceSelect.value = list[0].key;
        if (substanceCardsContainer.firstChild) substanceCardsContainer.firstChild.classList.add('active');
      }
    })
    .catch(() => {
      // fallback
      ['idealGas','steam','methane'].forEach(k => {
        const opt = document.createElement('option'); opt.value = k; opt.textContent = k; substanceSelect.appendChild(opt);
      });
      // render fallback cards
      const substanceCardsContainer = document.getElementById('substance-cards');
      substanceCardsContainer.innerHTML = '';
      ['idealGas','steam','methane'].forEach(k => {
        const card = document.createElement('div'); card.className = 'card'; card.textContent = k; card.onclick = () => { substanceSelect.value = k; Array.from(substanceCardsContainer.children).forEach(c => c.classList.remove('active')); card.classList.add('active'); }; substanceCardsContainer.appendChild(card);
      });
      substanceSelect.value = 'idealGas';
      if (substanceCardsContainer.firstChild) substanceCardsContainer.firstChild.classList.add('active');
    });

  form.addEventListener('submit', (ev) => {
    ev.preventDefault();
    const submitBtn = form.querySelector('button[type=submit]');
    submitBtn.disabled = true;
    const prevText = submitBtn.textContent;
    submitBtn.textContent = 'Calculating...';
    const formData = new FormData(form);
    const input_data = {};
    ['P1','V1','T1','P2','V2','T2','n'].forEach(k => {
      const v = formData.get(k);
      if (v !== null && v !== '') {
        input_data[k] = Number(v);
      }
    });

    const payload = {
      process_type: formData.get('process_type'),
      substance: formData.get('substance'),
      input_data: input_data,
      mass: Number(formData.get('mass')) || 1.0
    };

  resultsGrid.innerHTML = '<p style="color: var(--text-secondary); text-align: center;">Calculating...</p>';
  // Clear plots
  pvDiv.innerHTML = '';
  tsDiv.innerHTML = '';
  const pvDownload = document.getElementById('pv-download');
  const tsDownload = document.getElementById('ts-download');
  pvDownload.style.display = 'none';
  tsDownload.style.display = 'none';

    // Client-side validation per process type
    const formErrorsContainer = document.getElementById('form-errors');
    formErrorsContainer.innerHTML = '';
    function showFieldError(fieldId, msg) {
      let el = document.getElementById(fieldId + '-err');
      if (!el) {
        const input = document.getElementById(fieldId);
        el = document.createElement('div');
        el.id = fieldId + '-err';
        el.className = 'error';
        input.parentElement.appendChild(el);
      }
      el.textContent = msg;
    }
    function clearFieldErrors() {
      ['P1','V1','T1','P2','V2','T2','n'].forEach(k => {
        const el = document.getElementById(k + '-err');
        if (el) el.textContent = '';
      });
    }
    clearFieldErrors();

    const requiredByProcess = {
      constantVolume: [],
      constantPressure: [],
      isothermal: ['V2'],
      adiabatic: ['V2'],
      polytropic: ['V2','n'],
    };

    const proc = formData.get('process_type');
    const reqs = requiredByProcess[proc] || [];
    const errors = [];
    // Ensure base required inputs present
    ['P1','V1','T1'].forEach(k => {
      const v = formData.get(k);
      if (!v || v === '') {
        showFieldError(k, 'Required');
        errors.push(k + ' is required');
      } else if (Number(v) <= 0 || Number.isNaN(Number(v))) {
        showFieldError(k, 'Must be a positive number');
        errors.push(k + ' must be positive');
      }
    });
    // process-specific checks
    reqs.forEach(k => {
      const v = formData.get(k);
      if (!v || v === '') {
        showFieldError(k, 'Required for this process');
        errors.push(k + ' is required for ' + proc);
      } else if (Number(v) <= 0 || Number.isNaN(Number(v))) {
        showFieldError(k, 'Must be a positive number');
        errors.push(k + ' must be positive');
      }
    });

    if (errors.length > 0) {
      formErrorsContainer.textContent = errors.join('; ');
      submitBtn.disabled = false;
      submitBtn.textContent = prevText;
      return;
    }

    fetch('/calculate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    })
    .then(async res => {
      if (!res.ok) {
        const err = await res.json().catch(()=>({detail: 'unknown error'}));
        throw new Error(err.detail || 'Request failed');
      }
      return res.json();
    })
    .then(data => {
      // Display results in card format (omit plot data and input data)
      const result = data.result;
      const resultCards = [
        { label: 'P2', value: result.P2.toFixed(2), unit: 'kPa' },
        { label: 'V2', value: result.V2.toFixed(4), unit: 'm³' },
        { label: 'T2', value: result.T2.toFixed(2), unit: 'K' },
        { label: 'Work (W)', value: result.W.toFixed(4), unit: 'kJ' },
        { label: 'Heat (Q)', value: result.Q.toFixed(4), unit: 'kJ' },
        { label: 'ΔU', value: result.deltaU.toFixed(4), unit: 'kJ' },
        { label: 'ΔS', value: result.deltaS.toFixed(6), unit: 'kJ/K' },
      ];
      
      resultsGrid.innerHTML = resultCards.map(item => `
        <div class="result-card">
          <div class="result-card-label">${item.label}</div>
          <div class="result-card-value">${item.value}</div>
          <div class="result-card-label" style="font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.25rem;">${item.unit}</div>
        </div>
      `).join('');
      
      // Use pvData and tsData for interactive plots if available
      const pvDataArr = (data.result && data.result.pvData) || [];
      const tsDataArr = (data.result && data.result.tsData) || [];

      if (pvDataArr.length > 0) {
        const x = pvDataArr.map(p => p.V);
        const y = pvDataArr.map(p => p.P);
        const trace = { x, y, mode: 'lines+markers', name: 'P-V', line: {shape: 'spline'} };
        const layout = { xaxis: { title: 'V (m^3)' }, yaxis: { title: 'P (kPa)' }, margin: {t:30} };
        Plotly.newPlot(pvDiv, [trace], layout, {responsive: true});
        pvDownload.style.display = 'inline-block';
        pvDownload.onclick = async (e) => {
          e.preventDefault();
          const dataUrl = await Plotly.toImage(pvDiv, {format: 'png', width: 800, height: 500});
          pvDownload.href = dataUrl;
          pvDownload.download = `pv_plot_${Date.now()}.png`;
        };
      } else if (data.pv_plot) {
        // Fallback: insert image
        const img = document.createElement('img'); img.src = data.pv_plot; img.style.maxWidth = '100%'; pvDiv.appendChild(img);
        pvDownload.style.display = 'inline-block'; pvDownload.href = data.pv_plot; pvDownload.download = `pv_plot_${Date.now()}.png`;
      }

      if (tsDataArr.length > 0) {
        const x = tsDataArr.map(p => p.S);
        const y = tsDataArr.map(p => p.T);
        const trace = { x, y, mode: 'lines+markers', name: 'T-S', line: {shape: 'spline'} };
        const layout = { xaxis: { title: 'S (kJ/K)' }, yaxis: { title: 'T (K)' }, margin: {t:30} };
        Plotly.newPlot(tsDiv, [trace], layout, {responsive: true});
        tsDownload.style.display = 'inline-block';
        tsDownload.onclick = async (e) => {
          e.preventDefault();
          const dataUrl = await Plotly.toImage(tsDiv, {format: 'png', width: 800, height: 500});
          tsDownload.href = dataUrl;
          tsDownload.download = `ts_plot_${Date.now()}.png`;
        };
      } else if (data.ts_plot) {
        const img = document.createElement('img'); img.src = data.ts_plot; img.style.maxWidth = '100%'; tsDiv.appendChild(img);
        tsDownload.style.display = 'inline-block'; tsDownload.href = data.ts_plot; tsDownload.download = `ts_plot_${Date.now()}.png`;
      }
    })
    .catch(err => {
      resultsGrid.innerHTML = `<div style="grid-column: 1/-1; color: var(--error); padding: 1rem; text-align: center;">Error: ${err.message || err}</div>`;
    })
    .finally(() => {
      submitBtn.disabled = false;
      submitBtn.textContent = prevText;
    });
  });

  // Enable/disable inputs depending on process type
  const controls = {
    constantVolume: {V2:false, T2:true, n:false},
    constantPressure: {V2:true, T2:true, n:false},
    isothermal: {V2:true, T2:false, n:false},
    adiabatic: {V2:true, T2:false, n:false},
    polytropic: {V2:true, T2:false, n:true},
  };

  function setControlVisibility(type) {
    const cfg = controls[type] || {};
    ['V2','T2','n'].forEach(k => {
      const el = document.getElementById(k);
      if (!el) return;
      if (cfg[k]) {
        el.disabled = false;
        el.parentElement.style.opacity = '1';
      } else {
        el.disabled = true;
        el.parentElement.style.opacity = '0.5';
        el.value = '';
      }
    });
  }

  processSelect.addEventListener('change', (e) => setControlVisibility(e.target.value));
  // initialize
  setControlVisibility(processSelect.value || PROCESS_TYPES[0]);
});
