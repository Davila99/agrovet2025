// Real system metrics (extracted from system_metrics_20251120_181330.json)
const REAL_METRICS = {
  timestamp: '2025-11-20T18:13:28.702892',
  cpu_percent: 53.0,
  cpu_count: 8,
  per_cpu: [61.8,44.6,57.1,54.5,52.3,57.8,65.6,62.5],
  memory_total_gb: 7.2449798583984375,
  memory_used_gb: 6.218910217285156,
  memory_percent: 85.8,
  disk_free_gb: 281.7493553161621
};

document.addEventListener('DOMContentLoaded', ()=>{

  // Carousel logic
  const slidesEl = document.getElementById('slides');
  const slides = Array.from(document.querySelectorAll('.slide'));
  let current = 0;

  function show(idx){
    if(idx < 0) idx = 0;
    if(idx >= slides.length) idx = slides.length - 1;
    current = idx;
    const x = -idx * 100;
    slidesEl.style.transform = `translateX(${x}%)`;
    // trigger per-slide animation class
    slides.forEach((s,i)=>{
      s.classList.toggle('active', i===idx);
    });
    // initialize chart for this slide if needed
    const active = slides[idx];
    if(active) initChartForSlide(active);
    if(active) showExplanationFor(active);
  }

  document.getElementById('next').addEventListener('click', ()=> show(current+1));
  document.getElementById('prev').addEventListener('click', ()=> show(current-1));

  // also hook small next buttons inside slides
  document.querySelectorAll('.btn-next').forEach(b=> b.addEventListener('click', ()=>{
    const parent = b.closest('.slide');
    const idx = slides.indexOf(parent);
    show(idx+1);
  }));

  // reveal initial slide
  show(0);

  // Animate flow pulse and arrows
  const pulse = document.querySelector('.pulse');
  const arrowPaths = document.querySelectorAll('.arrow');

  function animatePath(path, delay=0){
    setTimeout(()=>{ path.style.strokeDashoffset = '0'; }, delay);
  }

  function resetPaths(){
    arrowPaths.forEach(p => p.style.strokeDashoffset = p.getTotalLength ? p.getTotalLength() : 200);
  }

  // initialize
  arrowPaths.forEach(p=>{
    const len = p.getTotalLength ? p.getTotalLength() : 200;
    p.style.strokeDasharray = len;
    p.style.strokeDashoffset = len;
  });

  // simple pulse animation along x axis
  let step = 0;
  function runPulse(){
    // positions correspond to the SVG layout
    const positions = [180, 300, 480];
    pulse.style.opacity = '1';
    pulse.style.transition = 'transform 900ms linear, opacity 300ms';
    pulse.style.transform = `translateX(${positions[step]-180}px)`;
    // animate arrow segments progressively
    if(step===0) animatePath(arrowPaths[0], 80);
    if(step===1) animatePath(arrowPaths[1], 80);
    step = (step + 1) % positions.length;
    setTimeout(()=>{ pulse.style.opacity='0' }, 900);
  }

  // loop the pulse every 1.6s
  runPulse();
  const pulseInterval = setInterval(runPulse, 1600);
  
  // Load Chart.js dynamically
  let ChartLibLoaded = false;
  function loadChartJs(cb){
    if(ChartLibLoaded) return cb();
    const s = document.createElement('script');
    // pin a stable Chart.js build for consistent API
    s.src = 'https://cdn.jsdelivr.net/npm/chart.js@3.9.1/dist/chart.min.js';
    s.onload = ()=>{ ChartLibLoaded = true; cb(); };
    s.onerror = ()=>{ console.warn('No se pudo cargar Chart.js desde CDN'); ChartLibLoaded = false; };
    document.head.appendChild(s);
  }

  // Simple fallback renderer when Chart.js is unavailable
  function renderFallbackChart(canvasId, labels, values, colors, type='bar'){
    const canvas = document.getElementById(canvasId);
    if(!canvas) return;
    const container = document.createElement('div');
    container.className = 'chart-fallback';
    container.style.display = 'grid';
    container.style.gap = '8px';
    container.style.marginTop = '8px';
    labels.forEach((lab, i)=>{
      const row = document.createElement('div');
      row.style.display = 'flex';
      row.style.alignItems = 'center';
      const label = document.createElement('div');
      label.textContent = lab;
      label.style.width = '160px';
      label.style.color = '#dceffb';
      const barWrap = document.createElement('div');
      barWrap.style.flex = '1';
      barWrap.style.background = 'rgba(255,255,255,0.03)';
      barWrap.style.borderRadius = '6px';
      barWrap.style.height = '12px';
      const bar = document.createElement('div');
      const v = values[i] || 0;
      bar.style.width = Math.min(100, v) + '%';
      bar.style.height = '100%';
      bar.style.background = colors && colors[i] ? colors[i] : '#0b77ff';
      bar.style.borderRadius = '6px';
      barWrap.appendChild(bar);
      const valueLabel = document.createElement('div');
      valueLabel.textContent = Array.isArray(v) ? ''+v : v + (type==='bar' ? '%' : '');
      valueLabel.style.width = '64px';
      valueLabel.style.textAlign = 'right';
      valueLabel.style.marginLeft = '12px';
      valueLabel.style.color = '#dceffb';
      row.appendChild(label);
      row.appendChild(barWrap);
      row.appendChild(valueLabel);
      container.appendChild(row);
    });
    canvas.parentNode.replaceChild(container, canvas);
  }

  const createdCharts = new Set();
  function initChartForSlide(slide){
    const id = slide.id;
    if(createdCharts.has(id)) return;
    // determine which chart to create
    if(id==='q1'){
      loadChartJs(()=> createCapacityChart());
    }else if(id==='q3'){
      loadChartJs(()=> createLatencyChart());
    }else if(id==='q4'){
      loadChartJs(()=> createBottlenecksChart());
    }else if(id==='q5'){
      loadChartJs(()=> createOptimChart());
    }else if(id==='monetization_model'){
      loadChartJs(()=> createMonetizationChart());
    }else if(id==='cicd'){
      loadChartJs(()=> createCIChart());
    }else if(id==='backend_endpoints'){
      loadChartJs(()=> createEndpointsChart());
    }else if(id==='backend_results'){
      loadChartJs(()=> createBackendResultsChart());
    }
    createdCharts.add(id);
    // also initialize diagrams if needed
    initDiagramForSlide(slide);
  }

  function initDiagramForSlide(slide){
    const id = slide.id;
    // mapping slide id to diagram generator
    const map = {
      'q1': createArchDiagram,
      'cicd': createTraefikDiagram,
      'backend_endpoints': createRedisDiagram,
      'q3': createAuthFlowDiagram
    };
    const gen = map[id];
    if(!gen) return;
    // avoid duplicate diagrams
    if(slide.querySelector('.diagram-svg')) return;
    const container = document.createElement('div');
    container.className = 'diagram-svg';
    container.innerHTML = gen();
    // insert before charts or at bottom
    const ref = slide.querySelector('.chart-container') || slide.querySelector('.answer-cards');
    if(ref) ref.parentNode.insertBefore(container, ref.nextSibling);
    else slide.appendChild(container);
  }

  // Diagram SVG generators (simple, responsive)
  function createArchDiagram(){
    return `
    <svg viewBox="0 0 900 240" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">
      <style>text{font-family:Inter,Arial,sans-serif;font-size:12px;fill:#07213a} .box{fill:#ffffff;stroke:#cfe9ff;stroke-width:1.5;filter:drop-shadow(0 8px 20px rgba(2,10,20,0.06))}</style>
      <rect x="20" y="20" width="860" height="48" rx="8" class="box" fill="#ffffff"/>
      <text x="450" y="52" text-anchor="middle" font-weight="700">API Gateway — Traefik</text>
      <!-- arrows down -->
      <line x1="150" y1="84" x2="150" y2="120" stroke="#9fcfff" stroke-width="3" stroke-linecap="round"/>
      <line x1="450" y1="84" x2="450" y2="120" stroke="#9fcfff" stroke-width="3" stroke-linecap="round"/>
      <line x1="750" y1="84" x2="750" y2="120" stroke="#9fcfff" stroke-width="3" stroke-linecap="round"/>
      <!-- service boxes -->
      <rect x="40" y="120" width="200" height="80" rx="8" class="box"/>
      <text x="140" y="155" text-anchor="middle">Auth Service</text>
      <rect x="340" y="120" width="200" height="80" rx="8" class="box"/>
      <text x="440" y="155" text-anchor="middle">Marketplace</text>
      <rect x="640" y="120" width="200" height="80" rx="8" class="box"/>
      <text x="740" y="155" text-anchor="middle">Chat / Foro</text>
      <!-- infra -->
      <rect x="220" y="210" width="140" height="40" rx="6" class="box"/>
      <text x="290" y="235" text-anchor="middle">Postgres</text>
      <rect x="380" y="210" width="140" height="40" rx="6" class="box"/>
      <text x="450" y="235" text-anchor="middle">Redis</text>
      <rect x="540" y="210" width="140" height="40" rx="6" class="box"/>
      <text x="610" y="235" text-anchor="middle">Kafka</text>
    </svg>`;
  }

  function createTraefikDiagram(){
    return `
    <svg viewBox="0 0 700 260" xmlns="http://www.w3.org/2000/svg">
      <style>text{font-family:Inter,Arial,sans-serif;font-size:12px;fill:#07213a}.box{fill:#fff;stroke:#cfe9ff;stroke-width:1.2}</style>
      <rect x="240" y="20" width="220" height="60" rx="8" class="box"/>
      <text x="350" y="55" text-anchor="middle" font-weight="700">Traefik</text>
      <text x="350" y="72" text-anchor="middle" font-size="11" fill="#556">(Entrypoint: 80, Dashboard: 8080)</text>
      <line x1="100" y1="100" x2="240" y2="50" stroke="#9fcfff" stroke-width="3"/>
      <text x="80" y="96" fill="#fff">Cliente</text>
      <line x1="350" y1="80" x2="350" y2="130" stroke="#9fcfff" stroke-width="2"/>
      <rect x="80" y="130" width="150" height="60" rx="8" class="box"/>
      <text x="155" y="165" text-anchor="middle">Auth :8002</text>
      <rect x="270" y="130" width="150" height="60" rx="8" class="box"/>
      <text x="345" y="165" text-anchor="middle">Media :8001</text>
      <rect x="460" y="130" width="150" height="60" rx="8" class="box"/>
      <text x="535" y="165" text-anchor="middle">Marketplace :8004</text>
    </svg>`;
  }

  function createRedisDiagram(){
    return `
    <svg viewBox="0 0 700 220" xmlns="http://www.w3.org/2000/svg">
      <style>text{font-family:Inter,Arial,sans-serif;font-size:12px;fill:#07213a}.c{fill:#fff;stroke:#cfe9ff;stroke-width:1.2}</style>
      <rect x="20" y="20" width="220" height="160" rx="10" class="c"/>
      <text x="130" y="48" text-anchor="middle" font-weight="700">Redis Server (6379)</text>
      <g transform="translate(40,70)">
        <rect x="0" y="0" width="160" height="30" rx="6" fill="#f7fbff" stroke="#d7eeff"/>
        <text x="80" y="20" text-anchor="middle">DB 0: Sessions</text>
        <rect x="0" y="40" width="160" height="30" rx="6" fill="#fff8e6" stroke="#ffedc2"/>
        <text x="80" y="60" text-anchor="middle">DB 1: Cache</text>
        <rect x="0" y="80" width="160" height="30" rx="6" fill="#eefcf0" stroke="#dff7de"/>
        <text x="80" y="100" text-anchor="middle">Channel Layers</text>
      </g>
    </svg>`;
  }

  function createAuthFlowDiagram(){
    return `
    <svg viewBox="0 0 720 220" xmlns="http://www.w3.org/2000/svg">
      <style>text{font-family:Inter,Arial,sans-serif;font-size:12px;fill:#07213a}.b{fill:#fff;stroke:#cfe9ff}</style>
      <rect x="20" y="20" width="120" height="60" rx="8" class="b"/>
      <text x="80" y="55" text-anchor="middle">Cliente</text>
      <rect x="220" y="20" width="160" height="60" rx="8" class="b"/>
      <text x="300" y="55" text-anchor="middle">Traefik</text>
      <rect x="460" y="20" width="160" height="60" rx="8" class="b"/>
      <text x="540" y="55" text-anchor="middle">Auth Service</text>
      <line x1="140" y1="50" x2="220" y2="50" stroke="#9fcfff" stroke-width="3" marker-end="url(#arrow)"/>
      <line x1="380" y1="50" x2="460" y2="50" stroke="#9fcfff" stroke-width="3" marker-end="url(#arrow)"/>
      <defs><marker id="arrow" markerWidth="10" markerHeight="10" refX="8" refY="5" orient="auto"><path d="M0,0 L10,5 L0,10 Z" fill="#9fcfff"/></marker></defs>
      <text x="360" y="90" text-anchor="middle">POST /api/auth/login → validate → token</text>
    </svg>`;
  }

  // Chart creation helpers (use estimates from docs)
  function createCapacityChart(){
    const ctx = document.getElementById('chart-capacity'); if(!ctx) return;
    // Use real system metrics to show resource headroom as proxy of capacity
    if(window.Chart){
      new Chart(ctx.getContext('2d'),{
        type:'bar',
        data:{labels:['CPU % usado','RAM % usado'],datasets:[{label:'Porcentaje',data:[REAL_METRICS.cpu_percent, REAL_METRICS.memory_percent],backgroundColor:['#0b77ff','#7cf57c']} ]},
        options:{responsive:true,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,max:100}}}
      });
    } else {
      renderFallbackChart('chart-capacity',['CPU % usado','RAM % usado'],[REAL_METRICS.cpu_percent, REAL_METRICS.memory_percent],['#0b77ff','#7cf57c'],'bar');
    }
  }

  function createLatencyChart(){
    const ctx = document.getElementById('chart-latency'); if(!ctx) return;
    if(window.Chart){
      new Chart(ctx.getContext('2d'),{
        type:'line',
        // Use estimated latency numbers from PERFORMANCE_AND_SCALABILITY.md as fallback
        data:{labels:['P50','P95','P99'],datasets:[{label:'Latencia (ms)',data:[180,450,800],borderColor:'#ff7a7a',backgroundColor:'rgba(255,122,122,0.08)',tension:0.3,pointRadius:6}]},
        options:{responsive:true,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true}}}
      });
    } else {
      renderFallbackChart('chart-latency',['P50','P95','P99'],[180,450,800],['#ff7a7a','#ff7a7a','#ff7a7a'],'bar');
    }
  }

  function createBottlenecksChart(){
    const ctx = document.getElementById('chart-bottlenecks'); if(!ctx) return;
    if(window.Chart){
      new Chart(ctx.getContext('2d'),{
        type:'doughnut',
        data:{labels:['DB (N+1)','Marketplace','Chat WS','Media Uploads','Otros'],datasets:[{data:[40,25,15,10,10],backgroundColor:['#0b77ff','#ffd27a','#7cf57c','#ff9fb3','#c7cbe6']}]},
        options:{responsive:true,plugins:{legend:{position:'bottom'}}}
      });
    } else {
      renderFallbackChart('chart-bottlenecks',['DB (N+1)','Marketplace','Chat WS','Media Uploads','Otros'],[40,25,15,10,10],['#0b77ff','#ffd27a','#7cf57c','#ff9fb3','#c7cbe6'],'bar');
    }
  }

  function createOptimChart(){
    const ctx = document.getElementById('chart-optim'); if(!ctx) return;
    if(window.Chart){
      new Chart(ctx.getContext('2d'),{
        type:'bar',
        data:{labels:['Latencia P95','RPS Máx','Cache Hit Ratio'],datasets:[{label:'Antes',data:[600,100,60],backgroundColor:'#ff9f66'},{label:'Después',data:[450,200,80],backgroundColor:'#7cf57c'}]},
        options:{responsive:true,plugins:{legend:{position:'bottom'}},scales:{y:{beginAtZero:true}}}
      });
    } else {
      renderFallbackChart('chart-optim',['Latencia P95','RPS Máx','Cache Hit Ratio'],[600,100,60],['#ff9f66','#ff9f66','#ff9f66'],'bar');
    }
  }


  // additional charts for new slides
  function createMonetizationChart(){
    const ctx = document.getElementById('chart-monetization'); if(!ctx) return;
    if(window.Chart){
      new Chart(ctx.getContext('2d'),{
        type:'pie',
        data:{labels:['Comisión','Suscripciones','Publicidad','Otros'],datasets:[{data:[60,30,8,2],backgroundColor:['#0b77ff','#7cf57c','#ffd27a','#c7cbe6']}]},
        options:{responsive:true,plugins:{legend:{position:'bottom'}}}
      });
    } else {
      renderFallbackChart('chart-monetization',['Comisión','Suscripciones','Publicidad','Otros'],[60,30,8,2],['#0b77ff','#7cf57c','#ffd27a','#c7cbe6'],'bar');
    }
  }

  function createCIChart(){
    const ctx = document.getElementById('chart-ci'); if(!ctx) return;
    if(window.Chart){
      new Chart(ctx.getContext('2d'),{
        type:'bar',
        data:{labels:['Tests','Build','Image Push','Deploy','Notifications'],datasets:[{label:'Steps automated',data:[1,1,1,1,1],backgroundColor:['#7cd1ff','#7cd1ff','#7cd1ff','#7cd1ff','#7cd1ff']}]},
        options:{responsive:true,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true,ticks:{stepSize:1}}}}
      });
    } else {
      renderFallbackChart('chart-ci',['Tests','Build','Image Push','Deploy','Notifications'],[1,1,1,1,1],['#7cd1ff','#7cd1ff','#7cd1ff','#7cd1ff','#7cd1ff'],'bar');
    }
  }

  function createEndpointsChart(){
    const ctx = document.getElementById('chart-endpoints'); if(!ctx) return;
    if(window.Chart){
      new Chart(ctx.getContext('2d'),{
        type:'bar',
        data:{labels:['Marketplace','Auth','Profiles','Chat WS'],datasets:[{label:'Relative load',data:[40,25,20,15],backgroundColor:['#ff9f66','#0b77ff','#7cf57c','#ffd27a']}]},
        options:{responsive:true,plugins:{legend:{display:false}},scales:{y:{beginAtZero:true}}}
      });
    } else {
      renderFallbackChart('chart-endpoints',['Marketplace','Auth','Profiles','Chat WS'],[40,25,20,15],['#ff9f66','#0b77ff','#7cf57c','#ffd27a'],'bar');
    }
  }

  function createBackendResultsChart(){
    const ctx = document.getElementById('chart-backend-results'); if(!ctx) return;
    if(window.Chart){
      new Chart(ctx.getContext('2d'),{
        type:'line',
        data:{labels:['Antes','Después'],datasets:[{label:'Latencia P95 (ms)',data:[600,450],borderColor:'#ff7a7a',backgroundColor:'rgba(255,122,122,0.08)'},{label:'Cache Hit (%)',data:[60,80],borderColor:'#7cf57c',backgroundColor:'rgba(124,245,124,0.08)'}]},
        options:{responsive:true,plugins:{legend:{position:'bottom'}}}
      });
    } else {
      renderFallbackChart('chart-backend-results',['Antes','Después'],[600,450],['#ff7a7a','#ff7a7a'],'bar');
    }
  }

  // Explanatory animations: per-slide explanations that fade/stagger in
  const explanations = {
    'q1': ['Estimación conservadora: 500–1,000 usuarios','Escalado horizontal permite 10k–20k','Recomendación: balanceo y réplicas por servicio'],
    'q3': ['Ramp-up causa latencias altas al inicio','Estabiliza en 30s con caching','Monitorear P95 y error rate durante la prueba'],
    'q4': ['N+1 queries: usar batch y select_related','Marketplace: añadir índices en filtros','Chat: limitar conexiones por instancia y shard Redis'],
    'q5': ['Caching con Redis (TTL optimizado)','Connection pooling y compresión Gzip','Paginación y reducción de payloads'],
    'monetization_model': ['Comisión por transacción: principal','Suscripciones premium para usuarios avanzados','Publicidad como complemento'],
    'cicd': ['Automatizar tests y build','Image push y despliegue a staging','Rollback y notificaciones automáticas'],
    'backend_endpoints': ['Marketplace: consultas y búsquedas complejas','Auth: picos en login','Chat: conexiones persistentes WS']
  };

  function showExplanationFor(slide){
    // remove existing explanation
    const existing = slide.querySelector('.explain');
    if(existing) existing.remove();
    const key = slide.id;
    const items = explanations[key];
    if(!items) return;
    const container = document.createElement('div');
    container.className = 'explain';
    const ul = document.createElement('ul');
    items.forEach((text, i)=>{
      const li = document.createElement('li');
      li.textContent = text;
      li.style.opacity = 0;
      li.style.transform = 'translateY(8px)';
      li.style.transition = `all 450ms ease ${i*120}ms`;
      ul.appendChild(li);
    });
    container.appendChild(ul);
    slide.appendChild(container);
    // trigger animate
    requestAnimationFrame(()=>{
      Array.from(container.querySelectorAll('li')).forEach(li=>{
        li.style.opacity = 1;
        li.style.transform = 'translateY(0)';
      });
    });
  }

  // Convert single paragraph answers into card layout for better readability
  function convertAnswersToCards(){
    slides.forEach(slide=>{
      const p = slide.querySelector('p.answer');
      if(!p) return;
      // Build cards grouping up to 2 sentences per card to keep text readable
      const raw = p.textContent.trim();
      const sentences = raw.split(/(?<=[.!?])\s+/).map(s=>s.trim()).filter(Boolean);
      const groups = [];
      for(let i=0;i<sentences.length;i+=2){
        const g = sentences.slice(i,i+2).join(' ');
        groups.push(g);
      }
      const container = document.createElement('div');
      container.className = 'answer-cards';
      groups.forEach((group, idx)=>{
        const card = document.createElement('div');
        card.className = 'answer-card';
        // keep first card with some emphasis: include original HTML for first card only
        if(idx===0){
          // try to preserve inline formatting for the first card
          card.innerHTML = p.innerHTML;
        } else {
          card.textContent = group;
        }
        container.appendChild(card);
      });
      // replace paragraph with container
      p.parentNode.replaceChild(container, p);
    });
  }

  // run conversion early
  convertAnswersToCards();

  // start preloading Chart.js and ensure diagrams are present for all slides
  try{
    loadChartJs(()=>{});
  }catch(e){console.warn('Chart pre-load failed', e)}
  slides.forEach(s => initDiagramForSlide(s));

  // clean up on unload
  window.addEventListener('beforeunload', ()=> clearInterval(pulseInterval));
});
