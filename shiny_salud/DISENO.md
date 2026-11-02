# Sistema visual

Base común de Dash y Shiny. El público es general: debe sentirse como un informe público que se puede interrogar, sereno, preciso y honesto con sus denominadores.

La dirección «Del censo a la ruta» abre con un relato oscuro, con escenas que avanzan al hacer scroll. El protagonista son los datos del proyecto: no usa imágenes generadas ni video.

## Elemento propio

La ruta. La navegación es una línea con nueve paradas, y las etapas del proyecto y del modelo repiten ese mismo dibujo. El diagrama de respuestas muestra la ruta real de las personas estudiadas.

## Color

Gama «Petróleo»: un neutro frío de fondo y azul petróleo como estructura, con el naranja reservado para quienes quedan fuera de la ruta formal. Los nombres de los tokens describen su función, no su tono, para poder cambiar la gama sin renombrar nada.

| Token | Valor | Uso |
|:--|:--|:--|
| `suelo` | `#EEF2F5` | Fondo de página |
| `pliego` | `#F7F9FB` | Controles y planos de lectura |
| `noche` | `#0B3C5D` | Cabecera, relato, banda de selección y pie |
| `acento` | `#8FC7E8` | La ruta, la cobertura y los botones sobre fondo oscuro |
| `tinta` | `#10293B` | Texto principal |
| `tinta-media` | `#3A4F60` | Texto secundario |
| `tinta-suave` | `#54697A` | Notas y ejes |
| `dentro` | `#1B6CA8` | **Dentro de la ruta formal**, acciones y modelo |
| `fuera` | `#DD6B20` | **Fuera de la ruta formal** |
| `grupo_a` y `grupo_b` | `#5B6FB5`, `#A86C00` | Comparar grupos: sexo o dificultad funcional |
| `referencia` | `#7D8A96` | Azar, prevalencia y otras líneas de referencia |
| `dentro-luz` y `fuera-luz` | `#4F9BD9`, `#D9703A` | Las mismas clases sobre `noche` |

Reglas:

- `fuera` no decora ni alerta: siempre es la clase «fuera de la ruta formal». Por eso los titulares no llevan palabras en color.
- `dentro`–`fuera` y `grupo_a`–`grupo_b` no se mezclan en una gráfica. Cada pareja pasó el validador de `dataviz` para daltonismo sobre `suelo`, y `dentro-luz` con `fuera-luz` sobre `noche`.
- El texto usa las tintas, nunca el color de la serie. Sobre superficies tenues, usar `#A84E12` para `fuera` y `#155A8C` para `dentro`.

## Superficies

Sin tarjetas, sombras ni degradados. La jerarquía la dan los planos de color y el espacio: las secciones se apoyan en el suelo, las cifras son una fila entre dos líneas y lo importante va en una banda de noche. La única sombra es la de BQSI abierto, porque flota sobre el contenido.

## Tipografía

Bricolage Grotesque para titulares y cifras. Atkinson Hyperlegible Next para texto, controles y datos: se diseñó para personas con baja visión, algo coherente con un proyecto que habla de dificultad funcional. Su cero lleva una barra para distinguirlo de la O. Ambas tienen licencia OFL y se sirven desde el propio proyecto.

Escala: texto 17 px con interlineado 1,6; notas 15 a 16 px; subtítulos 21 a 24 px; títulos de sección de 26 a 34 px; título de página de 37 a 60 px. Las etiquetas van en mayúscula inicial, nunca en mayúsculas.

## Componentes

- **Botón.** 46 px de alto, 4 px de radio y etiqueta 650. Principal, secundario y discreto, con estados de foco, cursor, presión y desactivado.
- **Selector de una opción.** Reemplaza a los botones de radio: la opción elegida se rellena de noche.
- **Banda de selección.** Filtros y resultado van juntos, para que se vea qué cambia cada filtro.
- **Frase viva.** Resume cada selección y solo enuncia un porcentaje cuando las reglas lo permiten.
- **Cinta de cobertura.** Muestra el estado del porcentaje, su motivo y la marca del mínimo de 80 %.
- **BQSI.** El chatbot es una pestaña acoplada al borde inferior, en `acento` para verse sobre fondos claros y oscuros, que se despliega como ventana de chat. Sus curvas más amplias lo separan del contenido del proyecto.

## Contenido

Las secciones leen `contenido.json` y se arman con bloques comunes. `tema.css` y `relato.css` son idénticos en las dos aplicaciones; `tema_dash.css` y `tema_shiny.css` solo adaptan cada marco.

## Nombre

`Salud Atlántico` es provisional. Se cambia en la constante `NOMBRE` de `dash_salud/generar_contenido.py`.

## Movimiento

El scroll dirigido se reserva para la apertura. Las herramientas de uso repetido responden sin demoras. Con movimiento reducido, las escenas cambian sin interpolación.

## Principios

1. Cada porcentaje se presenta con su denominador o su cobertura.
2. Un porcentaje oculto explica por qué y ofrece una alternativa cuando existe.
3. Una vista tiene una sola cifra protagonista.
4. Rejillas y ejes quedan en segundo plano.
5. Cada gráfica importante tiene etiquetas directas o una tabla.
6. Lo que se muestra nunca debe leerse como barrera, causa ni atención denegada.
