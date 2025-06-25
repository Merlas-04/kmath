// calculadora/static/js/funcion.js
console.log(">>> funcion.js: Script cargado.");

// Configuración de MathJax
window.MathJax = {
  startup: {
    ready: () => {
      console.log('MathJax está listo.');
      if (MathJax.startup.defaultReady) {
        MathJax.startup.defaultReady();
      }
    }
  },
  tex: {
    inlineMath: [['\\(', '\\)']],
    displayMath: [['\\[', '\\]']]
  },
  svg: {
    fontCache: 'global'
  }
};
console.log(">>> Configuración de MathJax aplicada.");


// --- FUNCIÓN PRINCIPAL DE LA CALCULADORA ---
function inicializarCalculadora() {
  console.log(">>> Entrando en inicializarCalculadora().");

  // --- Selección de Elementos del DOM ---
  const formulario = document.getElementById('formulario');
  const expresionInput = document.getElementById('expresion');
  const resultadoWrapper = document.getElementById('resultado-wrapper');
  const resultadoDiv = document.getElementById('resultado');
  const pasosDiv = document.getElementById('pasos');
  const historialListaElemento = document.getElementById('historial-lista');
  const btnLimpiarHistorial = document.getElementById('btn-limpiar-historial');
  const graficaContenedor = document.querySelector('.imagen-grafica');
  const graficaImg = document.getElementById('grafica-img');
  const btnVerGrafica = document.getElementById('btn-ver-grafica');
  const menuToggle = document.getElementById('menu-toggle');
  const historialPanel = document.querySelector('.historial');
  const overlay = document.getElementById('overlay'); // Elemento para el fondo oscuro

  if (!formulario || !expresionInput || !resultadoWrapper) {
    console.error("¡ERROR CRÍTICO! Faltan elementos esenciales. La aplicación no puede continuar.");
    return;
  }
  
  // ==========================================================
  // LÓGICA DE INTERFAZ DE USUARIO (UI)
  // ==========================================================

  if (menuToggle && historialPanel && overlay) {
    const toggleMenu = () => {
      historialPanel.classList.toggle('is-visible');
      overlay.classList.toggle('is-visible');
    };
    menuToggle.addEventListener('click', toggleMenu);
    overlay.addEventListener('click', toggleMenu); // Cierra el menú al hacer clic en el fondo
  }

  if (btnVerGrafica && graficaContenedor) {
    btnVerGrafica.addEventListener('click', () => {
      const isHidden = graficaContenedor.style.display === 'none';
      graficaContenedor.style.display = isHidden ? 'block' : 'none';
      btnVerGrafica.textContent = isHidden ? 'Ocultar Gráfica' : 'Ver Gráfica';
    });
  }

  // ==========================================================
  // LÓGICA DEL FORMULARIO PRINCIPAL
  // ==========================================================

  formulario.addEventListener('submit', function (e) {
    e.preventDefault();
    
    resultadoWrapper.style.display = 'block';
    resultadoDiv.innerHTML = '<p>Calculando...</p>';
    pasosDiv.innerHTML = '';
    graficaContenedor.style.display = 'none';
    graficaImg.src = "";
    graficaImg.alt = "Generando gráfica...";

    const expresion = expresionInput.value;
    if (!expresion) {
      resultadoDiv.innerHTML = '<p style="color: #E74C3C;">Por favor, introduce una expresión.</p>';
      return;
    }

    console.log("Enviando a /derivar:", expresion);

    fetch('/derivar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ expresion: expresion })
    })
    .then(response => {
      if (!response.ok) {
        return response.json().catch(() => null).then(errData => {
          throw new Error(errData?.error || `Error del servidor: ${response.status}`);
        });
      }
      return response.json();
    })
    .then(data => {
    // Si quieres, ya puedes eliminar o comentar la siguiente línea, ya que hemos resuelto el misterio.
    console.log("Respuesta de /derivar:", data); 

    if (data.resultado !== undefined && data.derivada_str !== undefined) {
        fetchAndRenderHistory();
        resultadoDiv.innerHTML = `<h2>Resultado:</h2><p>\\[${data.resultado}\\]</p>`;
        pasosDiv.innerHTML = `<h2>Explicación paso a paso:</h2><div>${data.pasos}</div>`;

        // --- INICIO DEL CÓDIGO CORREGIDO Y DEFINITIVO ---

        // Le pedimos a MathJax que espere a estar 100% listo y solo después
        // ejecute las funciones de renderizado y de la gráfica.
        // Esta es la forma oficial y más segura de manejar contenido dinámico.
        MathJax.startup.promise.then(() => {
            console.log('Confirmado: MathJax está listo. Renderizando ahora.');

            // Ahora que estamos seguros de que existe, llamamos a la función de renderizado.
            MathJax.typeset([resultadoDiv, pasosDiv]);

            // Y después de renderizar, pedimos la gráfica.
            solicitarGrafica(data.derivada_str);
        });

        // --- FIN DEL CÓDIGO CORREGIDO ---

    } else {
        throw new Error(data.error || "Respuesta inesperada del servidor.");
    }
})

  // ==========================================================
  // LÓGICA DEL HISTORIAL
  // ==========================================================

  if (btnLimpiarHistorial) {
    btnLimpiarHistorial.addEventListener('click', () => {
      if (!confirm('¿Estás seguro de que quieres borrar todo tu historial?')) return;
      
      historialListaElemento.innerHTML = '<li>Limpiando...</li>';
      fetch('/clear_history', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
          console.log("Respuesta de /clear_history:", data.message);
          fetchAndRenderHistory();
        })
        .catch(error => {
          console.error('Error al limpiar el historial:', error);
          alert('Error al limpiar el historial.');
          fetchAndRenderHistory();
        });
    });
  }

  function fetchAndRenderHistory() {
    if (!historialListaElemento) return;
    historialListaElemento.innerHTML = '<li>Cargando...</li>';

    fetch('/get_history')
      .then(response => {
        if (!response.ok) throw new Error('No se pudo obtener el historial.');
        return response.json();
      })
      .then(historyData => {
        historialListaElemento.innerHTML = '';
        if (historyData.length === 0) {
          historialListaElemento.innerHTML = '<li>(No hay cálculos)</li>';
          return;
        }
        historyData.forEach(item => {
          const li = document.createElement('li');
          li.textContent = `${item.expression} -> ${item.derivative}`;
          li.title = `Clic para cargar: ${item.expression}`;
          li.addEventListener('click', () => {
            expresionInput.value = item.expression;
            if(historialPanel && overlay) {
                historialPanel.classList.remove('is-visible');
                overlay.classList.remove('is-visible');
            }
          });
          historialListaElemento.appendChild(li);
        });
      })
      .catch(error => {
        console.error("Error al obtener historial:", error);
        historialListaElemento.innerHTML = `<li>Error al cargar.</li>`;
      });
  }

  // ==========================================================
  // LÓGICA DE LA GRÁFICA
  // ==========================================================

  function solicitarGrafica(expresionDerivada) {
    if (!graficaImg || !graficaContenedor) return;

    fetch('/graficar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ expresion: expresionDerivada })
    })
    .then(response => {
      if (!response.ok) {
        return response.json().catch(()=> null).then(errData => {
          throw new Error(errData?.error || `Error al graficar: ${response.status}`);
        });
      }
      return response.json();
    })
    .then(graphData => {
      if (graphData.image_base64) {
        graficaImg.src = `data:image/png;base64,${graphData.image_base64}`;
        graficaImg.alt = `Gráfica de: ${expresionDerivada}`;
      } else {
        throw new Error(graphData.error || "Respuesta de gráfica inválida.");
      }
    })
    .catch(error => {
      console.error('Error en fetch /graficar:', error);
      graficaImg.alt = `Error al generar gráfica: ${error.message}`;
    });
  }

  // Carga Inicial del Historial
  fetchAndRenderHistory();
  console.log(">>> inicializarCalculadora() completada.");
}

// --- LLAMADA PRINCIPAL ---
document.addEventListener('DOMContentLoaded', () => {
  console.log(">>> DOMContentLoaded evento disparado.");
  inicializarCalculadora();
});
