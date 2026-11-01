/* Asistente del proyecto, compartido por Dash y Shiny.
   El servidor decide qué cifras se pueden mostrar; este archivo solo envía la pregunta y los
   filtros, y escribe la respuesta como texto. */
(function () {
  "use strict";

  var SUGERENCIAS = ["¿Qué significa estar fuera de la ruta formal?", "¿Por qué algunos porcentajes se ocultan?", "¿Qué tan bueno es el modelo?"];
  var URL_PUBLICA = "https://dataviz-salud-atlantico-409319239507.us-east1.run.app/api/asistente";

  function urlServicio() {
    if (!window.Shiny) return "/api/asistente";
    return /^(localhost|127\.0\.0\.1)$/.test(location.hostname) ? "http://" + location.hostname + ":8050/api/asistente" : URL_PUBLICA;
  }

  function filtros() {
    if (!window.Shiny) return window.__filtrosActivos || {};
    var valor = function (id) { var e = document.getElementById(id); return e ? e.value : "Todos"; };
    var municipio = document.getElementById("f_municipio");
    var elegidos = municipio && municipio.selectize ? municipio.selectize.getValue() : [];
    return { municipios: elegidos || [], sexo: valor("f_sexo"), edad: valor("f_edad"), zona: valor("f_zona"), dificultad: valor("f_dificultad") };
  }

  function crear(etiqueta, clase, texto) {
    var e = document.createElement(etiqueta);
    if (clase) e.className = clase;
    if (texto !== undefined) e.textContent = texto;
    return e;
  }

  function iniciar() {
    if (document.querySelector(".asistente-abrir")) return;
    var abrir = crear("button", "boton asistente-abrir", "Preguntar sobre el proyecto");
    abrir.type = "button";
    abrir.setAttribute("aria-expanded", "false");

    var panel = crear("aside", "asistente");
    panel.hidden = true;
    panel.setAttribute("aria-label", "Asistente del proyecto");
    var cabeza = crear("div", "asistente-cabeza");
    var titulos = crear("div");
    titulos.appendChild(crear("strong", null, "Asistente del proyecto"));
    var estado = crear("span", "asistente-modo", "Comprobando…");
    titulos.appendChild(estado);
    var cerrar = crear("button", "asistente-cerrar", "Cerrar");
    cerrar.type = "button";
    cabeza.appendChild(titulos);
    cabeza.appendChild(cerrar);

    var conversacion = crear("div", "asistente-conversacion");
    conversacion.setAttribute("aria-live", "polite");
    var ayuda = crear("div", "asistente-ayuda");
    ayuda.appendChild(crear("p", null, "Responde con los documentos y datos agregados del proyecto, e indica de dónde sale cada respuesta. Cada pregunta se responde por separado."));
    var chips = crear("div", "asistente-sugerencias");
    SUGERENCIAS.forEach(function (texto) {
      var b = crear("button", "asistente-sugerencia", texto);
      b.type = "button";
      b.addEventListener("click", function () { preguntar(texto); });
      chips.appendChild(b);
    });
    ayuda.appendChild(chips);
    conversacion.appendChild(ayuda);

    var formulario = crear("form", "asistente-formulario");
    var campo = crear("textarea");
    campo.rows = 2;
    campo.maxLength = 500;
    campo.placeholder = "Escribe tu pregunta";
    campo.setAttribute("aria-label", "Tu pregunta");
    var enviar = crear("button", "boton", "Preguntar");
    enviar.type = "submit";
    formulario.appendChild(campo);
    formulario.appendChild(enviar);

    panel.appendChild(cabeza);
    panel.appendChild(conversacion);
    panel.appendChild(formulario);
    document.body.appendChild(abrir);
    document.body.appendChild(panel);

    function mostrarModo(modo) {
      var conectado = modo === "conectado";
      estado.textContent = conectado ? "Conectado a un modelo de lenguaje" : modo === "demostracion" ? "Demostración: extrae frases, sin modelo de lenguaje" : "Servicio no disponible";
      estado.className = "asistente-modo " + (conectado ? "conectado" : "demo");
    }

    function alternar(ver) {
      panel.hidden = !ver;
      abrir.hidden = ver;
      abrir.setAttribute("aria-expanded", String(ver));
      if (ver) {
        campo.focus();
        fetch(urlServicio() + "/estado").then(function (r) { return r.json(); })
          .then(function (d) { mostrarModo(d.modo); }).catch(function () { mostrarModo("error"); });
      } else {
        abrir.focus();
      }
    }

    function respuesta(d) {
      var caja = crear("div", "asistente-respuesta");
      caja.appendChild(crear("p", null, d.respuesta));
      if (d.filtros) {
        var f = crear("div", "asistente-filtros");
        f.appendChild(crear("strong", null, "Con tus filtros"));
        f.appendChild(crear("p", null, d.filtros.texto));
        caja.appendChild(f);
      }
      if (d.fuentes && d.fuentes.length) {
        var lista = crear("ol", "asistente-fuentes");
        d.fuentes.forEach(function (x) { lista.appendChild(crear("li", null, x.titulo + ". " + x.fuente)); });
        caja.appendChild(lista);
      }
      if (d.aviso) caja.appendChild(crear("p", "asistente-aviso", d.aviso));
      conversacion.appendChild(caja);
      if (d.modo) mostrarModo(d.modo);
    }

    function preguntar(texto) {
      var limpia = texto.trim();
      if (!limpia) return;
      ayuda.hidden = true;
      conversacion.appendChild(crear("p", "asistente-pregunta", limpia));
      var espera = crear("p", "asistente-espera", "Buscando en los documentos…");
      conversacion.appendChild(espera);
      conversacion.scrollTop = conversacion.scrollHeight;
      campo.value = "";
      enviar.disabled = true;
      fetch(urlServicio(), { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ pregunta: limpia, filtros: filtros() }) })
        .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
        .then(function (x) {
          espera.remove();
          if (x.ok) respuesta(x.d);
          else conversacion.appendChild(crear("p", "asistente-aviso", x.d.error || "No se pudo responder. Intenta de nuevo."));
        })
        .catch(function () {
          espera.remove();
          conversacion.appendChild(crear("p", "asistente-aviso", "El servicio no responde. Las demás secciones siguen funcionando."));
        })
        .then(function () { enviar.disabled = false; conversacion.scrollTop = conversacion.scrollHeight; campo.focus(); });
    }

    abrir.addEventListener("click", function () { alternar(true); });
    cerrar.addEventListener("click", function () { alternar(false); });
    panel.addEventListener("keydown", function (e) { if (e.key === "Escape") alternar(false); });
    formulario.addEventListener("submit", function (e) { e.preventDefault(); preguntar(campo.value); });
    campo.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); preguntar(campo.value); }
    });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
