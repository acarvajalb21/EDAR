# Sistema visual

Base común de Shiny y Dash. Debe sentirse como un informe público que se puede interrogar: sereno, preciso y honesto con sus denominadores.

La dirección «Del censo a la ruta» añade una apertura oscura y editorial, con escenas que avanzan al hacer scroll. Toma de las referencias su ritmo, su jerarquía y su uso del espacio, pero el protagonista son los datos del proyecto: no usa imágenes generadas ni video.

## Significado del color

El color significa lo mismo en toda la aplicación. Los nombres de los tokens describen su función, no su tono, para que cambiar la paleta no los vuelva engañosos.

| Token | Valor | Uso |
|:--|:--|:--|
| `fondo` | `#F3F5FA` | Fondo de página |
| `hoja` | `#FFFFFF` | Paneles y superficie de gráficas |
| `tinta` | `#141C33` | Texto principal |
| `tinta-media` | `#434C66` | Texto secundario |
| `tinta-suave` | `#5D6680` | Notas, ejes y barras neutras |
| `hilo` | `#DFE3EE` | Líneas finas y rejilla |
| `dentro` | `#2454D6` | **Dentro de la ruta formal**, acciones y modelo |
| `fuera` | `#E8505B` | **Fuera de la ruta formal** |
| `grupo_a` y `grupo_b` | `#008F88`, `#BC7A00` | Comparar grupos: sexo o dificultad funcional |
| `referencia` | `#9097A8` | Azar, prevalencia y otras líneas de referencia |
| `noche` | `#0F1830` | Fondo del relato y bandas de contraste |
| `dentro-luz` y `fuera-luz` | `#5A86F2`, `#EC5C78` | Las mismas clases sobre `noche` |

Reglas:

- `fuera` no se usa para decorar ni para alertar: siempre es la clase «fuera de la ruta formal».
- Las parejas `dentro`–`fuera` y `grupo_a`–`grupo_b` no se mezclan en una misma gráfica. Cada una pasó el validador de `dataviz` para daltonismo sobre `hoja`, y `dentro-luz` con `fuera-luz` lo pasó sobre `noche`.
- El texto usa las tintas, nunca el color de la serie. Sobre superficies tenues, usar `#B83240` para `fuera` y `#1B3FA8` para `dentro`.
- No hay selector de modo oscuro. Lo oscuro es una escena del relato, con su propia pareja de colores.

El Bookdown usa estos colores en sus páginas. Sus figuras PNG y el notebook conservan la paleta anterior hasta que el equipo apruebe esta.

## Tipografía

Bricolage Grotesque para titulares, cifras y frases protagonistas. Plus Jakarta Sans para texto, controles y datos. Ambas tienen licencia OFL y se sirven desde el propio proyecto. Como Bricolage no tiene cursiva, la palabra de acento de cada título se marca con color.

## Nombre

`Salud Atlántico` es provisional. El nombre se cambia en la constante `NOMBRE` de `dash_salud/generar_contenido.py`, y las dos aplicaciones lo leen de `contenido.json`.

## Elementos propios

- **Relato «Del censo a la ruta».** Cada cuadro representa un grupo de personas: 1.000 y luego 100. Termina en un mapa con las tasas publicadas. Los cuadros nunca representan a una persona real.
- **Frase viva.** Resume cada selección en una oración y solo enuncia una tasa cuando las reglas lo permiten.
- **Cinta de cobertura.** Acompaña a los filtros y muestra el estado de la tasa, su motivo y una barra con la marca del umbral del 80 %.
- **Diagrama de ruta.** El ancho de cada banda es proporcional a las personas que siguen esa ruta.

## Contenido

Las nueve secciones leen `contenido.json` y se arman con bloques comunes: párrafos, destacados, fichas, listas, etapas, tablas, barras, pestañas, preguntas y referencias. `contenido.css` les da el mismo aspecto en Dash y en Shiny. EDA multivariado y Modelo tienen controles propios.

## Movimiento

El scroll dirigido se reserva para la apertura. Las herramientas de uso repetido responden sin demoras. El movimiento es CSS y Canvas, sin librerías añadidas. Con movimiento reducido, las escenas cambian sin interpolación.

## Principios

1. Cada tasa se presenta con su denominador o su cobertura.
2. Una tasa oculta explica por qué y ofrece una alternativa cuando existe.
3. Una vista tiene una sola cifra protagonista.
4. Rejillas y ejes quedan en segundo plano; las líneas de datos tienen 2 a 2,5 px.
5. Cada gráfica importante tiene una alternativa en tabla o etiquetas directas.
6. Lo que se muestra nunca debe leerse como barrera, causa ni atención denegada.
