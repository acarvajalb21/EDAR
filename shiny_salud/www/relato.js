/* Relato de apertura «Del censo a la ruta». Compartido por Shiny y Dash.
   Cada cuadro representa a un grupo de personas, nunca a una persona real.
   Lee solo relato_datos.json: agregados publicables y geometría municipal. */
(function () {
  "use strict";

  var origen = document.currentScript ? document.currentScript.src.replace(/[^/]*$/, "") : "";
  var COLORES = [[247, 249, 251], [79, 155, 217], [217, 112, 58]]; // claro, dentro y fuera sobre noche
  var reducido = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function entero(n) { return String(Math.round(n)).replace(/\B(?=(\d{3})+$)/g, "."); }
  function pct(x, d) { return (100 * x).toFixed(d === undefined ? 1 : d).replace(".", ",") + " %"; }
  function limitar(v, a, b) { return Math.min(b, Math.max(a, v)); }
  function suave(v) { return v * v * (3 - 2 * v); }

  function pasos(d) {
    var dentro = d.cohorte - d.fuera;
    return [
      { clase: "paso-portada", html: '<p class="antetitulo">Censo de 2018 en el departamento del Atlántico</p>' +
        '<h1>Ante un problema de salud, ¿qué ruta se declaró?</h1>' +
        '<p class="entrada">Lo que respondieron las personas en el censo, y lo que esas respuestas no permiten afirmar.</p>' +
        '<div class="relato-acciones"><button type="button" class="relato-boton" data-ir="explorar">Comparar grupos</button>' +
        '<span class="relato-pista">Desliza para ver el relato</span></div>' },
      { html: "<h2>" + entero(d.flujo.people) + " personas en el censo.</h2><p>Cada cuadro representa a mil personas del Atlántico. Son grupos, no individuos.</p>" },
      { html: "<h2>" + entero(d.cohorte) + " declararon un problema de salud.</h2><p>Fue en los 30 días previos, sin hospitalización, y su respuesta se pudo clasificar. Son las personas estudiadas, no toda la población.</p>" },
      { html: "<h2>Acerquémonos.</h2><p>Ahora cada cuadro son cien personas. Todas respondieron qué hicieron principalmente ante ese problema.</p>" },
      { html: "<h2>Casi ocho de cada diez siguieron la ruta formal.</h2><p>" + entero(dentro) + " acudieron a su EPS y fueron atendidas, o a un médico particular. Otras " + entero(d.fuera) + " quedaron fuera de esa ruta: el " + pct(d.fuera / d.cohorte, 2) + ".</p>" },
      { html: "<h2>Fuera de la ruta no significa atención negada.</h2><p>Solo " + entero(d.rutas.eps_no_atendido) + " personas acudieron a su EPS y no recibieron atención. La mayoría declaró otra acción: " + entero(d.acciones.autorreceta) + " se autorrecetaron.</p>" },
      { html: "<h2>El patrón cambia con el territorio.</h2><p>Las diferencias pueden reflejar composición demográfica y otras características; no indican causas. Elige un municipio para explorarlo.</p>" },
      { clase: "paso-cierre", html: "<h2>Ahora explora tú.</h2><p>Compara grupos por municipio, edad, sexo, zona y dificultad funcional. Las cifras describen 2018 y siempre muestran cuántas personas hay detrás.</p>" +
        '<div class="relato-acciones"><button type="button" class="relato-boton" data-ir="explorar">Comparar grupos</button>' +
        '<button type="button" class="relato-boton secundario" data-ir="modelo">Ver el modelo</button></div>' }
    ];
  }

  // Dash no admite SVG en su diseño: el diagrama de ruta llega como atributo y se dibuja aquí.
  function pintarRuta(intentos) {
    var nodo = document.querySelector(".ruta-diagrama[data-svg]");
    if (nodo) nodo.innerHTML = nodo.getAttribute("data-svg");
    else if (!window.Shiny && intentos > 0) setTimeout(function () { pintarRuta(intentos - 1); }, 250);
  }
  pintarRuta(80);

  function irA(vista) {
    if (window.Shiny && window.Shiny.setInputValue) {
      window.Shiny.setInputValue("relato_ir", vista, { priority: "event" });
    } else if (window.dash_clientside && window.dash_clientside.set_props) {
      window.dash_clientside.set_props("nav", { value: vista });
    }
    window.scrollTo(0, 0);
  }

  function irMunicipio(nombre) {
    if (window.Shiny && window.Shiny.setInputValue) {
      window.Shiny.setInputValue("relato_municipio", nombre, { priority: "event" });
    } else if (window.dash_clientside && window.dash_clientside.set_props) {
      window.dash_clientside.set_props("sub-explorar", { value: "0" });
      window.dash_clientside.set_props("f-municipio", { value: [nombre] });
      window.dash_clientside.set_props("nav", { value: "explorar" });
    }
    window.scrollTo(0, 0);
  }

  // Reparte los cuadros de la clase por acción con el método del mayor residuo.
  function repartir(valores, total) {
    var suma = valores.reduce(function (a, b) { return a + b; }, 0);
    var exactos = valores.map(function (v) { return v * total / suma; });
    var bases = exactos.map(Math.floor);
    var faltan = total - bases.reduce(function (a, b) { return a + b; }, 0);
    exactos.map(function (v, i) { return [v - Math.floor(v), i]; })
      .sort(function (a, b) { return b[0] - a[0]; }).slice(0, faltan)
      .forEach(function (par) { bases[par[1]] += 1; });
    return bases;
  }

  function construir(raiz, d) {
    var lista = pasos(d);
    var total = Math.round(d.flujo.people / 1000);
    var cohorteMil = Math.round(d.cohorte / 1000);
    var cohorteCien = Math.round(d.cohorte / 100);
    var fueraCien = Math.round(d.fuera / 100);
    var dentroCien = cohorteCien - fueraCien;
    var grupos = [
      { nombre: "Se autorrecetó", n: d.acciones.autorreceta },
      { nombre: "Remedios caseros", n: d.acciones.remedios },
      { nombre: "No hizo nada", n: d.acciones.nada },
      { nombre: "Boticario o droguista", n: d.acciones.boticario },
      { nombre: "EPS sin atención", n: d.rutas.eps_no_atendido, destaca: true },
      { nombre: "Otras alternativas", n: d.acciones.otras }
    ];
    var cuadros = repartir(grupos.map(function (g) { return g.n; }), fueraCien);

    raiz.innerHTML =
      '<section class="relato" aria-label="Relato: del censo a la ruta declarada">' +
      '<div class="relato-escena"><canvas aria-hidden="true"></canvas><div class="relato-mapa"></div>' +
      '<div class="relato-etiquetas" aria-hidden="true"></div><p class="relato-escala" aria-hidden="true"></p></div>' +
      '<div class="relato-pasos">' + lista.map(function (p) {
        return '<article class="paso ' + (p.clase || "") + '"><div class="paso-texto">' + p.html + "</div></article>";
      }).join("") + "</div></section>";

    var seccion = raiz.querySelector(".relato");
    var escena = raiz.querySelector(".relato-escena");
    var lienzo = raiz.querySelector("canvas");
    var ctx = lienzo.getContext("2d");
    var capaMapa = raiz.querySelector(".relato-mapa");
    var capaEtiquetas = raiz.querySelector(".relato-etiquetas");
    var escala = raiz.querySelector(".relato-escala");
    var articulos = Array.prototype.slice.call(raiz.querySelectorAll(".paso"));
    var ESTADOS = 7;
    var X = [], Y = [], A = [], C = [], T = [];
    var semilla = new Float32Array(total);
    for (var i = 0; i < total; i++) semilla[i] = Math.abs(Math.sin(i * 12.9898) * 43758.5453) % 1;
    for (var k = 0; k < ESTADOS; k++) {
      X.push(new Float32Array(total)); Y.push(new Float32Array(total));
      A.push(new Float32Array(total)); C.push(new Uint8Array(total)); T.push(1);
    }
    var etiquetas = [];
    var W = 0, H = 0, proporcion = 1, actual = 0, objetivo = 0, pendiente = false, visible = true, ultimo = 0;

    function etiqueta(estado, html, clase) {
      var el = document.createElement("div");
      el.className = "relato-etiqueta " + (clase || "");
      el.innerHTML = html;
      capaEtiquetas.appendChild(el);
      etiquetas.push({ el: el, estado: estado });
      return el;
    }
    function ubicar(el, x, y) { el.style.transform = "translate(" + x.toFixed(1) + "px," + y.toFixed(1) + "px)"; }

    var rotDentro = etiqueta(4, "<strong>" + pct((d.cohorte - d.fuera) / d.cohorte, 2) + "</strong><span>dentro de la ruta formal</span>");
    var rotFuera = etiqueta(4, "<strong>" + pct(d.fuera / d.cohorte, 2) + "</strong><span>fuera de la ruta formal</span>");
    var rotGrupos = grupos.map(function (g) {
      return etiqueta(5, "<strong>" + entero(g.n) + "</strong><span>" + g.nombre + "</span>", g.destaca ? "destaca" : "");
    });

    function espiral(n, cx, cy, paso, destinoX, destinoY, desde) {
      for (var j = 0; j < n; j++) {
        var r = paso * Math.sqrt(j + 0.5), ang = j * 2.399963;
        destinoX[desde + j] = cx + r * Math.cos(ang);
        destinoY[desde + j] = cy + r * Math.sin(ang);
      }
    }

    function rejilla(x0, y0, ancho, alto, cx, cy, n) {
      var columnas = Math.ceil(Math.sqrt(n * ancho / alto));
      var filas = Math.ceil(n / columnas);
      var celda = Math.min(ancho / columnas, alto / filas);
      for (var j = 0; j < n; j++) {
        cx[j] = x0 + (ancho - columnas * celda) / 2 + (j % columnas) * celda + celda / 2;
        cy[j] = y0 + (alto - filas * celda) / 2 + Math.floor(j / columnas) * celda + celda / 2;
      }
      return celda;
    }

    function maquetar() {
      var caja = escena.getBoundingClientRect();
      if (caja.width < 10 || caja.height < 10) return;
      W = caja.width; H = caja.height;
      proporcion = Math.min(window.devicePixelRatio || 1, 2);
      lienzo.width = W * proporcion; lienzo.height = H * proporcion;
      var movil = W < 860;
      // El Dash parte su cabecera en dos filas en pantallas medianas.
      var cabecera = parseFloat(getComputedStyle(document.documentElement).getPropertyValue("--cabecera")) || 64;
      var alto = H - (cabecera - 64);
      var area = movil ? { x: 18, y: cabecera + 28, w: W - 36, h: alto * 0.42 - 16 } : { x: W * 0.47, y: cabecera + 32, w: W * 0.49, h: alto - 196 };

      // 0. Textura del censo a pantalla completa.
      T[0] = rejilla(-10, -10, W + 20, H + 20, X[0], Y[0], total) * 0.34;
      for (var j = 0; j < total; j++) { A[0][j] = j < cohorteMil ? 0.2 : 0.11; C[0][j] = 0; }
      // 1. El censo. 2. La cohorte: uno de cada diecisiete cuadros, repartido por la rejilla.
      T[1] = rejilla(area.x, area.y, area.w, area.h, X[1], Y[1], total) * 0.62;
      T[2] = T[1];
      var intervalo = total / cohorteMil;
      var orden = new Int32Array(total), usado = new Uint8Array(total), m = 0;
      for (j = 0; j < cohorteMil; j++) { var pos = Math.floor(j * intervalo); orden[j] = pos; usado[pos] = 1; }
      for (j = 0, m = cohorteMil; j < total; j++) if (!usado[j]) orden[m++] = j;
      for (j = 0; j < total; j++) {
        A[1][j] = 0.62; C[1][j] = 0;
        A[2][j] = j < cohorteMil ? 1 : 0.09; C[2][j] = j < cohorteMil ? 2 : 0;
      }
      var rx = X[1].slice(), ry = Y[1].slice();
      for (j = 0; j < total; j++) { X[1][j] = rx[orden[j]]; Y[1][j] = ry[orden[j]]; X[2][j] = X[1][j]; Y[2][j] = Y[1][j]; }

      // 3. Mil cuadros pasan a representar cien personas cada uno.
      var radio = Math.min(area.w, area.h) * 0.48;
      var pasoA = radio / Math.sqrt(cohorteCien);
      var cx = area.x + area.w / 2, cy = area.y + area.h / 2;
      espiral(cohorteCien, cx, cy, pasoA, X[3], Y[3], 0);
      T[3] = pasoA * 1.2;

      // 4. Las dos rutas.
      var unidades = 2 * (Math.sqrt(dentroCien) + Math.sqrt(fueraCien));
      var pasoB = Math.min((area.w - 34) / unidades, area.h * 0.46 / Math.sqrt(dentroCien));
      var rd = pasoB * Math.sqrt(dentroCien), rf = pasoB * Math.sqrt(fueraCien);
      var cxD = cx - (rf + 17), cxF = cx + (rd + 17);
      espiral(dentroCien, cxD, cy, pasoB, X[4], Y[4], 0);
      espiral(fueraCien, cxF, cy, pasoB, X[4], Y[4], dentroCien);
      T[4] = pasoB * 1.2;
      ubicar(rotDentro, cxD - 74, cy + rd + 10);
      ubicar(rotFuera, cxF - 74, cy + Math.max(rf, rd * 0.6) + 10);

      // 5. Dentro de la clase: las acciones declaradas.
      var columnas = 3, filas = 2;
      var celdaW = area.w / columnas, celdaH = area.h / filas;
      var mayor = Math.max.apply(null, cuadros);
      var pasoC = Math.min(celdaW, celdaH * 0.74) * 0.46 / Math.sqrt(mayor);
      for (j = 0; j < dentroCien; j++) { X[5][j] = X[4][j]; Y[5][j] = Y[4][j]; A[5][j] = 0; C[5][j] = 1; }
      var indice = dentroCien;
      cuadros.forEach(function (n, g) {
        var gx = area.x + celdaW * (g % columnas + 0.5), gy = area.y + celdaH * (Math.floor(g / columnas) + 0.36);
        espiral(n, gx, gy, pasoC, X[5], Y[5], indice);
        for (var h = 0; h < n; h++) { A[5][indice + h] = 1; C[5][indice + h] = grupos[g].destaca ? 0 : 2; }
        ubicar(rotGrupos[g], gx - 74, gy + celdaH * 0.3);
        indice += n;
      });
      T[5] = pasoC * 1.2;

      for (j = 0; j < total; j++) {
        var vive = j < cohorteCien;
        A[3][j] = vive ? 0.92 : 0; C[3][j] = 0;
        A[4][j] = vive ? 1 : 0; C[4][j] = j < dentroCien ? 1 : 2;
        if (!vive) {
          X[3][j] = X[2][j]; Y[3][j] = Y[2][j]; X[4][j] = X[2][j]; Y[4][j] = Y[2][j];
          X[5][j] = X[2][j]; Y[5][j] = Y[2][j]; A[5][j] = 0; C[5][j] = 0;
        }
        X[6][j] = X[5][j]; Y[6][j] = Y[5][j]; A[6][j] = 0; C[6][j] = C[5][j];
      }
      T[6] = T[5];

      var relacion = d.mapa.alto / d.mapa.ancho;
      var anchoMapa = Math.min(area.w, area.h / relacion);
      // En pantallas bajas la leyenda va al lado del mapa para que el texto no la tape.
      var lateral = movil && H < 640;
      capaMapa.classList.toggle("lateral", lateral);
      capaMapa.style.width = anchoMapa + "px";
      capaMapa.style.left = (lateral ? area.x : area.x + (area.w - anchoMapa) / 2) + "px";
      capaMapa.style.top = area.y + (area.h - anchoMapa * relacion) / 2 + "px";
      pendiente = true; pintar();
    }

    function dibujar(t) {
      ctx.setTransform(proporcion, 0, 0, proporcion, 0, 0);
      ctx.clearRect(0, 0, W, H);
      var k = Math.min(Math.floor(t), ESTADOS - 2), f = limitar(t - k, 0, 1);
      var xa = X[k], xb = X[k + 1], ya = Y[k], yb = Y[k + 1], aa = A[k], ab = A[k + 1], ca = C[k], cb = C[k + 1];
      var ta = T[k] + (T[k + 1] - T[k]) * suave(f);
      for (var j = 0; j < total; j++) {
        var local = reducido ? Math.round(f) : suave(limitar(f * 1.45 - semilla[j] * 0.45, 0, 1));
        var alfa = aa[j] + (ab[j] - aa[j]) * local;
        if (alfa < 0.012) continue;
        var c1 = COLORES[ca[j]], c2 = COLORES[cb[j]];
        ctx.fillStyle = "rgba(" + (c1[0] + (c2[0] - c1[0]) * local | 0) + "," + (c1[1] + (c2[1] - c1[1]) * local | 0) + "," + (c1[2] + (c2[2] - c1[2]) * local | 0) + "," + alfa.toFixed(3) + ")";
        ctx.fillRect(xa[j] + (xb[j] - xa[j]) * local - ta / 2, ya[j] + (yb[j] - ya[j]) * local - ta / 2, ta, ta);
      }
      etiquetas.forEach(function (e) { e.el.style.opacity = limitar(1.6 - Math.abs(t - e.estado) * 2.4, 0, 1).toFixed(2); });
      var verMapa = limitar((t - 5.4) * 2.4, 0, 1);
      capaMapa.style.opacity = verMapa.toFixed(2);
      var interactivo = verMapa > 0.9;
      if (interactivo !== capaMapa.classList.contains("interactivo")) {
        capaMapa.classList.toggle("interactivo", interactivo);
        // Lo invisible no recibe foco de teclado.
        capaMapa.querySelectorAll("path[role=button]").forEach(function (trazo) { trazo.setAttribute("tabindex", interactivo ? "0" : "-1"); });
      }
      escala.style.opacity = t > 5.5 || t < 0.5 ? 0 : 1;
      escala.textContent = t < 2.5 ? "1 cuadro = 1.000 personas" : "1 cuadro = 100 personas";
    }

    function pintar(ahora) {
      // El amortiguado depende del tiempo: un equipo lento no se queda atrás del scroll.
      var dt = Math.min(ahora && ultimo ? ahora - ultimo : 16, 400);
      ultimo = ahora || 0;
      if (reducido) { actual = objetivo; }
      else { actual += (objetivo - actual) * (1 - Math.exp(-dt / 105)); }
      if (Math.abs(objetivo - actual) < 0.002) actual = objetivo;
      if (W > 0) dibujar(actual);
      if (actual !== objetivo && visible) requestAnimationFrame(pintar);
      else { pendiente = false; ultimo = 0; }
    }

    function alDesplazar() {
      var caja = seccion.getBoundingClientRect();
      var centro = window.innerHeight / 2 - caja.top;
      var previo = articulos[0].offsetTop + articulos[0].offsetHeight * 0.5;
      var t = 0;
      for (var j = 1; j < articulos.length; j++) {
        var siguiente = articulos[j].offsetTop + articulos[j].offsetHeight / 2;
        if (centro >= previo) t = j - 1 + limitar((centro - previo) / (siguiente - previo), 0, 1);
        previo = siguiente;
      }
      objetivo = limitar(t, 0, ESTADOS - 1);
      articulos.forEach(function (a, n) { a.classList.toggle("activo", Math.abs(t - n) < 0.62); });
      if (!pendiente) { pendiente = true; requestAnimationFrame(pintar); }
    }

    // Mapa municipal con las tasas ya publicadas; se atenúa lo que no alcanza el mínimo.
    var conDato = d.mapa.municipios.filter(function (m) { return m.n; });
    var tasas = conDato.map(function (m) { return m.sin_formal / m.n; });
    var minimo = Math.min.apply(null, tasas), maximo = Math.max.apply(null, tasas);
    var svgNS = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("viewBox", "0 0 " + d.mapa.ancho + " " + d.mapa.alto);
    svg.setAttribute("role", "group");
    svg.setAttribute("aria-label", "Mapa del Atlántico: porcentaje fuera de la ruta formal por municipio");
    var aviso = document.createElement("div");
    aviso.className = "relato-aviso";
    aviso.textContent = "Elige un municipio para explorarlo";
    d.mapa.municipios.forEach(function (m) {
      var trazo = document.createElementNS(svgNS, "path");
      trazo.setAttribute("d", m.trazo);
      var titulo = document.createElementNS(svgNS, "title");
      if (m.n) {
        var v = (m.sin_formal / m.n - minimo) / (maximo - minimo);
        trazo.setAttribute("fill", "rgb(" + Math.round(31 + 186 * v) + "," + Math.round(84 + 28 * v) + "," + Math.round(117 - 59 * v) + ")");
        var texto = m.municipio + ": " + pct(m.sin_formal / m.n) + " · base aproximada " + entero(m.n);
        titulo.textContent = texto;
        trazo.setAttribute("tabindex", "-1");
        trazo.setAttribute("role", "button");
        trazo.setAttribute("aria-label", texto + ". Explorar este municipio");
        trazo.addEventListener("mouseenter", function () { aviso.textContent = texto; });
        trazo.addEventListener("focus", function () { aviso.textContent = texto; });
        trazo.addEventListener("click", function () { irMunicipio(m.municipio); });
        trazo.addEventListener("keydown", function (e) {
          if (e.key === "Enter" || e.key === " ") { e.preventDefault(); irMunicipio(m.municipio); }
        });
      } else {
        trazo.setAttribute("class", "sin-dato");
        titulo.textContent = m.municipio + ": no alcanza el mínimo de publicación";
        trazo.addEventListener("mouseenter", function () { aviso.textContent = titulo.textContent; });
      }
      trazo.appendChild(titulo);
      svg.appendChild(trazo);
    });
    capaMapa.appendChild(svg);
    var leyenda = document.createElement("div");
    leyenda.className = "relato-leyenda";
    leyenda.innerHTML = "<b>Fuera de la ruta formal</b><span>" + pct(minimo) + "</span><i></i><span>" + pct(maximo) + "</span>";
    capaMapa.appendChild(leyenda);
    capaMapa.appendChild(aviso);

    raiz.addEventListener("click", function (e) {
      var boton = e.target.closest ? e.target.closest("[data-ir]") : null;
      if (boton) irA(boton.getAttribute("data-ir"));
    });

    window.addEventListener("scroll", alDesplazar, { passive: true });
    window.addEventListener("resize", function () { maquetar(); alDesplazar(); });
    if (window.ResizeObserver) new ResizeObserver(function () { maquetar(); alDesplazar(); }).observe(escena);
    if (window.IntersectionObserver) {
      new IntersectionObserver(function (entradas) {
        visible = entradas[0].isIntersecting;
        document.documentElement.classList.toggle("relato-a-la-vista", visible);
        if (visible) alDesplazar();
      }, { rootMargin: "-64px 0px 0px 0px" }).observe(seccion);
    }
    maquetar();
    alDesplazar();
    articulos[0].classList.add("activo");
  }

  function iniciar() {
    var raiz = document.getElementById("relato");
    if (!raiz || raiz.getAttribute("data-listo")) return;
    raiz.setAttribute("data-listo", "1");
    fetch(origen + "relato_datos.json").then(function (r) { return r.json(); })
      .then(function (d) { construir(raiz, d); })
      .catch(function () { raiz.removeAttribute("data-listo"); });
  }

  new MutationObserver(iniciar).observe(document.documentElement, { childList: true, subtree: true });
  iniciar();
})();
