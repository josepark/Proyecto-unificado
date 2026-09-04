/* SUIIN-RBAC — comportamiento del lado del cliente.
 * Centralizado aquí (en vez de atributos onclick/onchange inline) para que
 * la Content-Security-Policy pueda exigir script-src 'self' sin
 * 'unsafe-inline' (ISO/IEC 27002:2022 — 8.26 seguridad de aplicaciones). */
(function () {
  "use strict";

  // Formularios con confirmación: <form data-confirm="mensaje">
  document.addEventListener("submit", function (ev) {
    var form = ev.target;
    if (form && form.hasAttribute && form.hasAttribute("data-confirm")) {
      if (!window.confirm(form.getAttribute("data-confirm"))) {
        ev.preventDefault();
      }
    }
  });

  // Campos que envían su formulario al cambiar: <select data-auto-submit>
  document.addEventListener("change", function (ev) {
    var el = ev.target;
    if (el && el.hasAttribute && el.hasAttribute("data-auto-submit") && el.form) {
      el.form.submit();
    }
  });

  // Selector de nivel asignado por usuario: recolorea según el valor elegido
  document.addEventListener("change", function (ev) {
    var el = ev.target;
    if (el && el.classList && el.classList.contains("nivel-asig")) {
      var v = el.value === "—" ? "X" : el.value;
      el.className = "nivel-asig asig-" + v;
    }
  });

  // ---- Ayuda dinámica de MFA según el rol elegido (alta y edición) ----
  var configurarAyudaMfa = function (rol, mfaSel, hint) {
    if (!rol || !mfaSel || !hint) { return; }
    var actualizar = function () {
      var op = rol.options[rol.selectedIndex];
      var req = op ? (op.getAttribute("data-mfa") || "") : "";
      if (!req) { hint.textContent = ""; return; }
      var activo = mfaSel.value.indexOf("Sí") === 0;
      if (req.indexOf("Sí") === 0 && !activo) {
        hint.textContent = "Este rol exige MFA (" + req + ").";
        hint.className = "campo hint-alerta";
      } else {
        hint.textContent = req === "No" ? "" : "Requisito de MFA del rol: " + req;
        hint.className = "campo hint-ok";
      }
    };
    rol.addEventListener("change", actualizar);
    mfaSel.addEventListener("change", actualizar);
    actualizar();
  };

  configurarAyudaMfa(document.getElementById("alta-rol"),
                     document.getElementById("alta-mfa"),
                     document.getElementById("alta-mfa-hint"));
  configurarAyudaMfa(document.getElementById("editar-rol"),
                     document.getElementById("editar-mfa"),
                     document.getElementById("editar-mfa-hint"));

  // ---- Alta de usuario: vigencia condicionada al estado Temporal ----
  var formAlta = document.getElementById("form-alta-usuario");
  if (formAlta) {
    var estado = document.getElementById("alta-estado");
    var contIni = document.getElementById("alta-fecha-inicio-cont");
    var contFin = document.getElementById("alta-fecha-fin-cont");
    var fin = document.getElementById("alta-fecha-fin");
    var ini = document.getElementById("alta-fecha-inicio");
    var vigenciaHint = document.getElementById("alta-vigencia-hint");

    var actualizarVigencia = function () {
      var temporal = estado.value === "Temporal";
      contIni.style.display = temporal ? "" : "none";
      contFin.style.display = temporal ? "" : "none";
      ini.required = temporal;
      fin.required = temporal;
      vigenciaHint.style.display = temporal ? "" : "none";
    };

    estado.addEventListener("change", actualizarVigencia);

    formAlta.addEventListener("submit", function (ev) {
      if (estado.value === "Temporal" && ini.value && fin.value && fin.value < ini.value) {
        ev.preventDefault();
        window.alert("La fecha de fin no puede ser anterior a la de inicio.");
      }
    });

    actualizarVigencia();
  }

  // ---- Editar usuario: coherencia de fechas de vigencia ----
  var formEditar = document.getElementById("form-editar-usuario");
  if (formEditar) {
    formEditar.addEventListener("submit", function (ev) {
      var ini = formEditar.querySelector('input[name="fecha_inicio"]');
      var fin = formEditar.querySelector('input[name="fecha_fin"]');
      if (ini.value && fin.value && fin.value < ini.value) {
        ev.preventDefault();
        window.alert("La fecha de fin no puede ser anterior a la de inicio.");
      }
    });
  }

  // ---- Catálogo de técnicas MITRE ATT&CK (buscador con selección múltiple) ----
  var catalogosAttack = document.querySelectorAll("[data-catalogo-attack]");
  if (catalogosAttack.length) {
    // La URL viene del atributo data- del <body> (ver base.html), resuelta
    // por Flask con url_for() — así funciona igual en pie (127.0.0.1:5000)
    // que detrás del gateway bajo /rbac/. Una ruta absoluta hardcodeada
    // como "/static/attack_tecnicas.json" se rompía bajo el prefijo: el
    // navegador la pedía en la raíz del dominio, que en el despliegue
    // integrado sirve los estáticos del Inventario, no los de RBAC.
    var urlCatalogo = document.body.getAttribute("data-attack-catalog-url") || "/static/attack_tecnicas.json";
    fetch(urlCatalogo)
      .then(function (r) { return r.json(); })
      .then(function (datos) {
        catalogosAttack.forEach(function (cont) {
          inicializarCatalogoAttack(cont, datos);
        });
      })
      .catch(function () { /* si falla la carga, el campo queda inactivo */ });
  }

  function inicializarCatalogoAttack(cont, datos) {
    var input = cont.querySelector(".catalogo-buscar");
    var lista = cont.querySelector(".catalogo-lista");
    var chips = cont.querySelector(".catalogo-chips");
    var oculto = cont.querySelector(".catalogo-valor");
    var porId = {};
    datos.forEach(function (t) { porId[t.id] = t; });

    var seleccion = (oculto.value || "")
      .split("/").map(function (s) { return s.trim().toUpperCase(); })
      .filter(Boolean);

    function pintarChips() {
      oculto.value = seleccion.join("/");
      chips.innerHTML = "";
      seleccion.forEach(function (id) {
        var t = porId[id];
        var chip = document.createElement("span");
        chip.className = "chip-attack" + (t ? "" : " chip-desconocida");
        var texto = document.createElement("span");
        texto.textContent = t ? (id + " — " + t.nombre) : (id + " (no reconocida)");
        chip.appendChild(texto);
        var quitar = document.createElement("button");
        quitar.type = "button";
        quitar.textContent = "\u00d7";
        quitar.setAttribute("aria-label", "Quitar " + id);
        quitar.addEventListener("click", function () {
          seleccion = seleccion.filter(function (x) { return x !== id; });
          pintarChips();
        });
        chip.appendChild(quitar);
        chips.appendChild(chip);
      });
    }

    function buscar() {
      var q = input.value.trim().toLowerCase();
      lista.innerHTML = "";
      if (!q) { lista.hidden = true; return; }
      var coincidencias = datos.filter(function (t) {
        return seleccion.indexOf(t.id) === -1 &&
          (t.id.toLowerCase().indexOf(q) !== -1 ||
           t.nombre.toLowerCase().indexOf(q) !== -1);
      }).slice(0, 25);
      coincidencias.forEach(function (t) {
        var op = document.createElement("div");
        op.className = "catalogo-opcion";
        var b = document.createElement("b");
        b.textContent = t.id;
        op.appendChild(b);
        op.appendChild(document.createTextNode(" — " + t.nombre));
        op.addEventListener("click", function () {
          seleccion.push(t.id);
          input.value = "";
          lista.hidden = true;
          pintarChips();
          input.focus();
        });
        lista.appendChild(op);
      });
      lista.hidden = coincidencias.length === 0;
    }

    input.addEventListener("input", buscar);
    input.addEventListener("focus", buscar);
    document.addEventListener("click", function (ev) {
      if (!cont.contains(ev.target)) { lista.hidden = true; }
    });

    pintarChips();
  }

  // ---- Matriz: guardar cada celda sin recargar la página, con "Deshacer" ----
  var celdasMatriz = document.querySelectorAll("form[data-matriz-celda]");
  if (celdasMatriz.length) {
    celdasMatriz.forEach(function (form) {
      var select = form.querySelector("select.nivel");
      select.addEventListener("change", function () {
        guardarCeldaMatriz(form, select);
      });
    });
  }

  function toastMatriz() {
    var div = document.getElementById("toast-matriz");
    if (!div) {
      div = document.createElement("div");
      div.id = "toast-matriz";
      div.className = "toast-envoltura";
      document.body.appendChild(div);
    }
    return div;
  }

  function guardarCeldaMatriz(form, select) {
    var datos = new FormData(form);
    select.disabled = true;
    fetch(form.action, {
      method: "POST",
      body: datos,
      headers: { "X-Requested-With": "XMLHttpRequest" }
    }).then(function (resp) {
      return resp.json().then(function (cuerpo) {
        return { ok: resp.ok, cuerpo: cuerpo };
      });
    }).then(function (res) {
      select.disabled = false;
      if (!res.ok || !res.cuerpo.ok) {
        mostrarToastSimple(
          (res.cuerpo && res.cuerpo.mensaje) || "No se pudo guardar el cambio.", true);
        return;
      }
      var c = res.cuerpo;
      select.className = "nivel niv-" + (c.nuevo === "—" ? "X" : c.nuevo);
      mostrarToastCambio(form, select, c);
    }).catch(function () {
      select.disabled = false;
      mostrarToastSimple("No se pudo guardar el cambio: revise la conexión.", true);
    });
  }

  function mostrarToastCambio(form, select, c) {
    var div = toastMatriz();
    div.innerHTML = "";
    var texto = document.createElement("span");
    texto.textContent = "Guardado: " + c.rol + " × " + c.sistema + ": " +
      c.anterior + " → " + c.nuevo;
    div.appendChild(texto);
    var deshacer = document.createElement("button");
    deshacer.type = "button";
    deshacer.className = "toast-deshacer";
    deshacer.textContent = "Deshacer";
    deshacer.addEventListener("click", function () {
      select.value = c.anterior;
      guardarCeldaMatriz(form, select);
    });
    div.appendChild(deshacer);
    div.className = "toast-envoltura visible";
    clearTimeout(div._temporizador);
    div._temporizador = setTimeout(function () {
      div.classList.remove("visible");
    }, 8000);
  }

  function mostrarToastSimple(mensaje, esError) {
    var div = toastMatriz();
    div.innerHTML = "";
    var texto = document.createElement("span");
    texto.textContent = mensaje;
    div.appendChild(texto);
    div.className = "toast-envoltura visible" + (esError ? " toast-error" : "");
    clearTimeout(div._temporizador);
    div._temporizador = setTimeout(function () {
      div.classList.remove("visible");
    }, 5000);
  }

  // ---- Matriz: búsqueda rápida de sistema (desplaza y resalta la fila) ----
  var buscadorMatriz = document.getElementById("matriz-buscar");
  if (buscadorMatriz) {
    var irAFilaMatriz = function () {
      var q = buscadorMatriz.value.trim().toLowerCase();
      if (!q) { return; }
      var encontrada = null;
      document.querySelectorAll(".matriz tr[data-sistema]").forEach(function (fila) {
        if (!encontrada && fila.getAttribute("data-sistema").indexOf(q) !== -1) {
          encontrada = fila;
        }
      });
      if (encontrada) {
        encontrada.scrollIntoView({ block: "center", behavior: "smooth" });
        encontrada.classList.add("fila-resaltada");
        setTimeout(function () {
          encontrada.classList.remove("fila-resaltada");
        }, 2200);
      }
    };
    buscadorMatriz.addEventListener("keydown", function (ev) {
      if (ev.key === "Enter") {
        ev.preventDefault();
        irAFilaMatriz();
      }
    });
  }
})();
