// app.js - Enhanced version with better UX

// ---------- Helper UI functions ----------
function showAlert(html, isError=false) {
  const alerts = document.getElementById('alerts');
  alerts.innerHTML = `<div class="alert ${isError ? 'error' : ''}">${html}</div>`;
}

function clearAlert() {
  document.getElementById('alerts').innerHTML = '';
}

function showResultsSection() {
  const section = document.getElementById('resultsSection');
  section.style.display = 'block';
  setTimeout(() => {
    section.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }, 100);
}

// ---------- Model status polling ----------
async function checkModelStatus() {
  const btn = document.getElementById('predictBtn');
  const nutBtn = document.getElementById('predictNutBtn');
  
  try {
    const res = await fetch('/model_status');
    const data = await res.json();
    
    if (data.fitted) {
      clearAlert();
      btn.disabled = false;
      nutBtn.disabled = false;
      btn.innerHTML = '<span class="btn-icon">🧠</span><span class="btn-text">Find Recipes</span>';
      nutBtn.innerHTML = '<span class="btn-icon">🔬</span><span class="btn-text">Nutrition Match</span>';
    } else {
      btn.disabled = true;
      nutBtn.disabled = true;
      
      if (data.fitting) {
        showAlert('⏳ AI Model is loading... This may take 10–60 seconds on first run. Please wait.');
        btn.innerHTML = '<span class="btn-icon">⏳</span><span class="btn-text">Loading AI Model...</span>';
        nutBtn.innerHTML = '<span class="btn-icon">⏳</span><span class="btn-text">Loading AI Model...</span>';
      } else {
        showAlert('⏳ Preparing AI model... Please refresh in a few seconds.');
        btn.innerHTML = '<span class="btn-icon">⏳</span><span class="btn-text">Preparing...</span>';
        nutBtn.innerHTML = '<span class="btn-icon">⏳</span><span class="btn-text">Preparing...</span>';
      }
      
      setTimeout(checkModelStatus, 2000);
    }
  } catch (err) {
    showAlert('⚠️ Could not connect to server. Please make sure the server is running.', true);
    btn.disabled = true;
    nutBtn.disabled = true;
    setTimeout(checkModelStatus, 4000);
  }
}

// ---------- Render results ----------
function renderResults(results) {
  const container = document.getElementById('results');
  const countEl = document.getElementById('resultCount');
  
  container.innerHTML = '';
  
  if (!results || results.length === 0) {
    container.innerHTML = '<div class="empty">😔 No recipes found. Try different ingredients or broader criteria.</div>';
    countEl.textContent = 'No results';
    showResultsSection();
    return;
  }

  countEl.textContent = `Found ${results.length} delicious recipe${results.length !== 1 ? 's' : ''}`;

  results.forEach(r => {
    const card = document.createElement('div');
    card.className = 'card';

    const imgHtml = r.image_url 
      ? `<img src="${r.image_url}" class="card-img" alt="${r.title || 'Recipe'}" loading="lazy">` 
      : '<div class="card-img" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); display: flex; align-items: center; justify-content: center; color: white; font-size: 3rem;">🍽️</div>';
    
    const title = r.title || r.name || 'Untitled Recipe';
    const prep = r.prep_time || r.minutes || '';
    const matchPct = r.final_score ? Math.round((r.final_score || 0) * 100) : '';
    
    // Format nutrition data nicely
    let nutritionHtml = '';
    if (r.nutrition_pred && Object.keys(r.nutrition_pred).length > 0) {
      const nutritionItems = Object.entries(r.nutrition_pred)
        .map(([k, v]) => {
          const icon = k === 'calories' ? '🔥' : k === 'protein' ? '💪' : k === 'fat' ? '🥑' : '🌾';
          return `${icon} ${k}: ${Math.round(v)}`;
        })
        .join(' • ');
      nutritionHtml = `<div class="nutrition"><strong>Predicted Nutrition:</strong><br>${nutritionItems}</div>`;
    }
    
    const distHtml = (typeof r.nutrition_distance === 'number') 
      ? `<div style="font-size: 0.85rem; color: #888; margin-top: 8px;">Match Score: ${(100 - r.nutrition_distance * 100).toFixed(0)}%</div>` 
      : '';

    const ingredients = (r.ingredients || 'N/A').split(',').slice(0, 8).join(', ');
    const moreIngredients = (r.ingredients || '').split(',').length > 8 ? '...' : '';

    card.innerHTML = `
      ${imgHtml}
      <div class="card-body">
        <h3>${title}</h3>
        <div class="meta">
          ${prep ? `⏱️ ${prep} min` : ''} 
          ${matchPct ? `• 🎯 ${matchPct}% match` : ''}
        </div>
        ${nutritionHtml}
        ${distHtml}
        <div class="ingredients">
          <strong>🥘 Ingredients:</strong>
          ${ingredients}${moreIngredients}
        </div>
        <details>
          <summary>📖 Show Instructions</summary>
          <p>${r.instructions || 'No instructions available.'}</p>
        </details>
      </div>
    `;
    
    container.appendChild(card);
  });

  showResultsSection();
}

// ---------- Basic predictions (no nutrition) ----------
async function getPredictions() {
  const btn = document.getElementById('predictBtn');
  if (!btn || btn.disabled) return;

  const ingredients = document.getElementById('ingredients').value.trim();
  const max_time = document.getElementById('max_time').value;
  
  if (!ingredients) {
    showAlert('🥕 Please enter at least one ingredient to find recipes!');
    document.getElementById('ingredients').focus();
    return;
  }
  
  clearAlert();
  btn.disabled = true;
  btn.innerHTML = '<span class="btn-icon">⏳</span><span class="btn-text">Searching...</span>';

  const payload = { ingredients, max_time };
  
  try {
    const res = await fetch('/recommend', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    
    if (res.status === 401) {
      window.location.href = '/login';
      return;
    }
    
    if (res.status === 503) {
      showAlert('⏳ AI Model is still loading. Please wait a moment and try again.');
      btn.disabled = false;
      btn.innerHTML = '<span class="btn-icon">🧠</span><span class="btn-text">Find Recipes</span>';
      return;
    }
    
    const data = await res.json();
    
    if (data.error) {
      showAlert('❌ Error: ' + data.error, true);
    } else {
      renderResults(data.results);
    }
  } catch (err) {
    showAlert('❌ Failed to connect to server. Make sure the Python server is running!', true);
    console.error('Request error:', err);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span class="btn-icon">🧠</span><span class="btn-text">Find Recipes</span>';
  }
}

// ---------- Nutrition-aware predictions ----------
async function getPredictionsWithNutrition() {
  const btn = document.getElementById('predictNutBtn');
  if (!btn || btn.disabled) return;

  const ingredients = document.getElementById('ingredients').value.trim();
  const max_time = document.getElementById('max_time').value;
  const calories = document.getElementById('target_calories').value;
  const protein = document.getElementById('target_protein').value;
  const tolerance = document.getElementById('tolerance').value || "0.2";

  if (!ingredients) {
    showAlert('🥕 Please enter at least one ingredient to find recipes!');
    document.getElementById('ingredients').focus();
    return;
  }

  if (!calories && !protein) {
    showAlert('🎯 Please set at least one nutrition target (calories or protein).');
    return;
  }

  clearAlert();
  btn.disabled = true;
  btn.innerHTML = '<span class="btn-icon">⏳</span><span class="btn-text">Analyzing...</span>';

  const nutrition_target = {};
  if (calories) nutrition_target['calories'] = Number(calories);
  if (protein) nutrition_target['protein'] = Number(protein);

  const payload = { ingredients, max_time, nutrition_target, tolerance };

  try {
    const res = await fetch('/recommend_with_nutrition', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    
    if (res.status === 401) {
      window.location.href = '/login';
      return;
    }
    
    if (res.status === 503) {
      showAlert('⏳ AI Model is still loading. Please wait a moment and try again.');
      btn.disabled = false;
      btn.innerHTML = '<span class="btn-icon">🔬</span><span class="btn-text">Nutrition Match</span>';
      return;
    }
    
    const data = await res.json();
    
    if (data.error) {
      showAlert('❌ Error: ' + data.error, true);
    } else {
      if (data.results && data.results.length === 0) {
        showAlert('😔 No recipes matched your nutrition targets within the tolerance range. Try increasing tolerance or adjusting targets.');
      }
      renderResults(data.results || []);
    }
  } catch (err) {
    showAlert('❌ Failed to contact server for nutrition predictions.', true);
    console.error('Request error:', err);
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span class="btn-icon">🔬</span><span class="btn-text">Nutrition Match</span>';
  }
}

// ---------- Initialize on page load ----------
window.addEventListener('load', () => {
  // Start model status polling
  checkModelStatus();

  // Wire up button event listeners
  const btn = document.getElementById('predictBtn');
  if (btn) btn.addEventListener('click', getPredictions);

  const nutBtn = document.getElementById('predictNutBtn');
  if (nutBtn) nutBtn.addEventListener('click', getPredictionsWithNutrition);

  // Allow Enter key to trigger search
  const ingredientsInput = document.getElementById('ingredients');
  if (ingredientsInput) {
    ingredientsInput.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        getPredictions();
      }
    });
  }
});