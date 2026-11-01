# Sistema visual «Papel censal»

Base común de Shiny, Dash, Bookdown y el notebook del modelo. Evoca el papel y la tinta de un formulario censal, y el río y la arcilla del Atlántico. Debe sentirse como un informe público que se puede interrogar: sereno, preciso y honesto con sus denominadores.

## Significado del color

El color significa lo mismo en todos los productos.

| Token | Valor | Uso |
|:--|:--|:--|
| `papel` | `#F4F1E9` | Fondo de página |
| `hoja` | `#FDFCF9` | Paneles y superficie de gráficas |
| `tinta` | `#13232C` | Texto principal |
| `tinta-media` | `#465660` | Texto secundario |
| `tinta-suave` | `#5F6D75` | Notas y ejes |
| `hilo` | `#DDD8CB` | Líneas finas y rejilla |
| `rio` | `#00739A` | **Dentro de la ruta formal**, acciones y modelo |
| `arcilla` | `#C4552D` | **Fuera de la ruta formal** |
| `anil` y `ocre` | `#3F5AA6`, `#B57A08` | Comparar grupos: sexo o dificultad funcional |
| `referencia` | `#9A978C` | Azar, prevalencia y otras líneas de referencia |

Reglas:

- Arcilla no se usa para decorar ni para alertar: siempre es la clase «fuera de la ruta formal».
- Las parejas río–arcilla y añil–ocre no se mezclan en una misma gráfica. Cada pareja pasó el validador de `dataviz` para daltonismo sobre `hoja`.
- El texto usa las tintas, nunca el color de la serie. Sobre superficies tenues, usar `#A5441F` para arcilla y `#005C7B` para río.
- No hay modo oscuro. Es una decisión deliberada para mantener un solo conjunto validado.

## Tipografía

IBM Plex Sans en todos los productos web, con licencia OFL y servida desde el propio proyecto. Pesos 400, 500 y 600. Las cifras grandes usan números proporcionales y las columnas, números tabulares. Las figuras estáticas usan esa fuente solo si está instalada.

## Elementos propios

- **Diagrama de ruta.** El ancho de cada banda es proporcional a las personas que siguen esa ruta.
- **Cinta de cobertura.** Acompaña a los filtros y muestra el estado de la tasa, su motivo y una barra con la marca del umbral del 80 %.

## Principios

1. Cada tasa se presenta con su denominador o su cobertura.
2. Una tasa oculta explica por qué y ofrece una alternativa cuando existe.
3. Una vista tiene una sola cifra protagonista.
4. Rejillas y ejes quedan en segundo plano; las líneas de datos tienen 2 a 2,5 px.
5. Cada gráfica importante tiene una alternativa en tabla o etiquetas directas.
6. Lo que se muestra nunca debe leerse como barrera, causa ni atención denegada.
