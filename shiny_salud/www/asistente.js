/* BQSI, el asistente del proyecto, compartido por Dash y Shiny.
   Es una pestaña acoplada al borde inferior que se despliega hacia arriba. El servidor decide
   qué cifras se pueden mostrar; este archivo solo envía la pregunta, los filtros y los turnos
   recientes, y escribe la respuesta como texto. */
(function () {
  "use strict";

  var NOMBRE = "BQSI";
  var INVITACION = "¿Tienes una pregunta?";
  var INICIO = ["¿Qué significa estar fuera de la ruta formal?", "¿Qué municipio tiene el mayor porcentaje?",
                "¿Qué tan bueno es el modelo?", "¿Qué limitaciones tiene el análisis?"];
  var NOMBRES = { panorama: "Introducción", objetivos: "Objetivos", problema: "Problema", marco: "Marco teórico", univariado: "EDA univariado",
                  explorar: "EDA multivariado", creacion: "Modelado", modelo: "Modelo", conclusiones: "Conclusiones" };
  var CHEVRON = "M3 10.5 8 5.5l5 5";
  var FLECHA = "M8 13V3M3.5 7.5 8 3l4.5 4.5";
  var URL_PUBLICA = "https://dataviz-salud-atlantico-409319239507.us-east1.run.app/api/asistente";
  var URL_INFORME = "https://acarvajalb21.github.io/EDAR/";

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

  function resumenFiltros() {
    var f = filtros();
    var partes = (f.municipios || []).slice();
    ["sexo", "edad", "zona", "dificultad"].forEach(function (k) { if (f[k] && f[k] !== "Todos") partes.push(f[k]); });
    return partes.join(", ");
  }

  function irASeccion(id) {
    if (window.Shiny && window.Shiny.setInputValue) window.Shiny.setInputValue("relato_ir", id, { priority: "event" });
    else if (window.dash_clientside && window.dash_clientside.set_props) window.dash_clientside.set_props("nav", { value: id });
  }

  function crear(etiqueta, clase, texto) {
    var e = document.createElement(etiqueta);
    if (clase) e.className = clase;
    if (texto !== undefined) e.textContent = texto;
    return e;
  }

  function boton(clase, texto, alHacerClic) {
    var b = crear("button", clase, texto);
    b.type = "button";
    b.addEventListener("click", alHacerClic);
    return b;
  }

  function icono(clase, trazo) {
    var ns = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(ns, "svg");
    var linea = document.createElementNS(ns, "path");
    svg.setAttribute("class", clase);
    svg.setAttribute("viewBox", "0 0 16 16");
    svg.setAttribute("aria-hidden", "true");
    linea.setAttribute("d", trazo);
    svg.appendChild(linea);
    return svg;
  }

  function iniciar() {
    if (document.querySelector(".asistente")) return;
    var historial = [];
    var modo = null;

    var panel = crear("aside", "asistente");
    panel.setAttribute("aria-label", NOMBRE + ", asistente del proyecto");

    var barra = crear("div", "asistente-barra");
    var pestana = boton("asistente-pestana", undefined, function () { alternar(!panel.classList.contains("abierto")); });
    pestana.setAttribute("aria-expanded", "false");
    pestana.setAttribute("aria-controls", "asistente-cuerpo");
    pestana.appendChild(crear("span", "asistente-marca"));
    var nombres = crear("span", "asistente-nombres");
    nombres.appendChild(crear("strong", null, NOMBRE));
    var estado = crear("span", "asistente-modo", INVITACION);
    nombres.appendChild(estado);
    pestana.appendChild(nombres);
    pestana.appendChild(icono("asistente-chevron", CHEVRON));
    var nueva = boton("asistente-nueva", "Nueva", reiniciar);
    nueva.setAttribute("aria-label", "Nueva conversación");
    barra.appendChild(pestana);
    barra.appendChild(nueva);

    var conversacion = crear("div", "asistente-conversacion");
    conversacion.setAttribute("aria-live", "polite");
    var contexto = crear("p", "asistente-contexto");
    contexto.hidden = true;

    var formulario = crear("form", "asistente-formulario");
    var campo = crear("textarea");
    campo.rows = 1;
    campo.maxLength = 500;
    campo.placeholder = "Escribe tu pregunta";
    campo.setAttribute("aria-label", "Tu pregunta");
    var enviar = crear("button", "asistente-enviar");
    enviar.type = "submit";
    enviar.setAttribute("aria-label", "Enviar pregunta");
    enviar.appendChild(icono("asistente-flecha", FLECHA));
    formulario.appendChild(campo);
    formulario.appendChild(enviar);

    var cuerpo = crear("div", "asistente-cuerpo");
    cuerpo.id = "asistente-cuerpo";
    cuerpo.inert = true;
    var recorte = crear("div", "asistente-recorte");
    var interior = crear("div", "asistente-interior");
    interior.appendChild(conversacion);
    interior.appendChild(contexto);
    interior.appendChild(formulario);
    recorte.appendChild(interior);
    cuerpo.appendChild(recorte);

    panel.appendChild(barra);
    panel.appendChild(cuerpo);
    document.body.appendChild(panel);

    function fila() {
      var caja = crear("div", "asistente-fila");
      var globo = crear("div", "asistente-globo");
      caja.appendChild(crear("span", "asistente-marca"));
      caja.appendChild(globo);
      return { caja: caja, globo: globo };
    }

    function sugerencias(preguntas) {
      var grupo = crear("div", "asistente-sugerencias");
      preguntas.forEach(function (p) { grupo.appendChild(boton("asistente-sugerencia", p, function () { preguntar(p); })); });
      return grupo;
    }

    function bienvenida() {
      var saludo = fila();
      saludo.globo.appendChild(crear("p", null, "Hola, soy " + NOMBRE + ". Respondo sobre los datos, los indicadores, el modelo y los límites de este proyecto, y te digo de dónde sale cada respuesta."));
      conversacion.appendChild(saludo.caja);
      conversacion.appendChild(sugerencias(INICIO));
    }

    function reiniciar() {
      historial = [];
      conversacion.textContent = "";
      bienvenida();
      campo.focus({ preventScroll: true });
    }

    function mostrarModo(valor) {
      modo = valor;
      if (!panel.classList.contains("abierto")) return;
      var conectado = valor === "conectado";
      estado.textContent = !valor ? "Comprobando…" : conectado ? "Conectado a un modelo de lenguaje" : valor === "demostracion" ? "Demostración, sin modelo de lenguaje" : "Servicio no disponible";
      estado.classList.toggle("conectado", conectado);
    }

    function mostrarContexto() {
      var texto = resumenFiltros();
      contexto.hidden = !texto;
      contexto.textContent = texto ? "Usando tus filtros: " + texto : "";
    }

    function alternar(ver) {
      panel.classList.toggle("abierto", ver);
      pestana.setAttribute("aria-expanded", String(ver));
      cuerpo.inert = !ver;
      if (ver) {
        mostrarContexto();
        mostrarModo(modo);
        campo.focus({ preventScroll: true });
        fetch(urlServicio() + "/estado").then(function (r) { return r.json(); })
          .then(function (d) { mostrarModo(d.modo); }).catch(function () { mostrarModo("error"); });
      } else {
        estado.textContent = INVITACION;
        estado.classList.remove("conectado");
        pestana.focus();
      }
    }

    function fuentes(lista) {
      var caja = crear("details", "asistente-fuentes-caja");
      caja.open = lista.length <= 2;
      caja.appendChild(crear("summary", null, lista.length === 1 ? "Fuente" : "Fuentes (" + lista.length + ")"));
      var ol = crear("ol", "asistente-fuentes");
      lista.forEach(function (x) {
        // Una respuesta de referencia ya se titula con la pregunta: basta decir de dónde viene.
        var li = crear("li", null, (/\?$/.test(x.titulo) ? "" : x.titulo + ". ") + x.fuente + ". ");
        if (x.seccion && NOMBRES[x.seccion]) {
          li.appendChild(boton("asistente-enlace-fuente", "Ir a " + NOMBRES[x.seccion], function () {
            irASeccion(x.seccion);
            if (window.innerWidth <= 760) alternar(false);
          }));
        } else if (x.pagina && /^[a-z0-9-]+\.html$/.test(x.pagina)) {
          var a = crear("a", "asistente-enlace-fuente", "Abrir en el informe");
          a.href = (window.Shiny ? URL_INFORME : "/informe/") + x.pagina;
          a.target = "_blank";
          a.rel = "noopener noreferrer";
          li.appendChild(a);
        }
        ol.appendChild(li);
      });
      caja.appendChild(ol);
      return caja;
    }

    function respuesta(d) {
      var mensaje = fila();
      mensaje.globo.appendChild(crear("p", null, d.respuesta));
      if (d.filtros) {
        var f = crear("div", "asistente-filtros");
        f.appendChild(crear("strong", null, "Con tus filtros"));
        f.appendChild(crear("p", null, d.filtros.texto));
        mensaje.globo.appendChild(f);
      }
      if (d.terminos && d.terminos.length) {
        var terminos = crear("details", "asistente-terminos");
        terminos.appendChild(crear("summary", null, "Qué significan los términos"));
        d.terminos.forEach(function (t) {
          var nota = crear("p", "asistente-termino");
          nota.appendChild(crear("strong", null, t.termino + ": "));
          nota.appendChild(document.createTextNode(t.definicion));
          terminos.appendChild(nota);
        });
        mensaje.globo.appendChild(terminos);
      }
      if (d.fuentes && d.fuentes.length) mensaje.globo.appendChild(fuentes(d.fuentes));
      if (d.aviso) mensaje.globo.appendChild(crear("p", "asistente-aviso", d.aviso));
      conversacion.appendChild(mensaje.caja);
      if (d.sugerencias && d.sugerencias.length) conversacion.appendChild(sugerencias(d.sugerencias));
      if (d.modo) mostrarModo(d.modo);
    }

    function esperando() {
      var espera = fila();
      var puntos = crear("div", "asistente-espera");
      puntos.appendChild(crear("span", "asistente-oculto", NOMBRE + " está buscando en los documentos"));
      for (var i = 0; i < 3; i++) puntos.appendChild(crear("i"));
      espera.globo.appendChild(puntos);
      conversacion.appendChild(espera.caja);
      return espera.caja;
    }

    function error(texto) {
      var mensaje = fila();
      mensaje.globo.appendChild(crear("p", "asistente-aviso", texto));
      conversacion.appendChild(mensaje.caja);
    }

    function ajustarCampo() {
      campo.style.height = "auto";
      campo.style.height = campo.scrollHeight + "px";
    }

    function preguntar(texto) {
      var limpia = texto.trim();
      if (!limpia || enviar.disabled) return;
      Array.prototype.forEach.call(conversacion.querySelectorAll(".asistente-sugerencias"), function (g) { g.remove(); });
      mostrarContexto();
      var burbuja = crear("p", "asistente-pregunta", limpia);
      conversacion.appendChild(burbuja);
      var espera = esperando();
      espera.scrollIntoView({ block: "end" });
      campo.value = "";
      ajustarCampo();
      enviar.disabled = true;
      fetch(urlServicio(), { method: "POST", headers: { "Content-Type": "application/json" },
                             body: JSON.stringify({ pregunta: limpia, filtros: filtros(), historial: historial }) })
        .then(function (r) { return r.json().then(function (d) { return { ok: r.ok, d: d }; }); })
        .then(function (x) {
          espera.remove();
          if (x.ok) {
            respuesta(x.d);
            historial = historial.concat([{ pregunta: limpia, respuesta: x.d.respuesta }]).slice(-4);
          } else {
            error(x.d.error || "No se pudo responder. Intenta de nuevo.");
          }
        })
        .catch(function () {
          espera.remove();
          error("El servicio no responde. Las demás secciones siguen funcionando.");
        })
        .then(function () {
          enviar.disabled = false;
          burbuja.scrollIntoView({ block: "start" });
          campo.focus({ preventScroll: true });
        });
    }

    panel.addEventListener("keydown", function (e) { if (e.key === "Escape" && panel.classList.contains("abierto")) alternar(false); });
    formulario.addEventListener("submit", function (e) { e.preventDefault(); preguntar(campo.value); });
    campo.addEventListener("input", ajustarCampo);
    campo.addEventListener("keydown", function (e) {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); preguntar(campo.value); }
    });
    bienvenida();
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", iniciar);
  else iniciar();
})();
