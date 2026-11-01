# Protocolo del modelo con contexto de salud (30 de octubre de 2026)

Este documento se fijó **antes** de consultar la validación con estas variables. Conserva la cohorte, la etiqueta, las particiones y la regla de sustitución del [protocolo de octubre](../experimentos_2026_10/PROTOCOLO.md). Mientras no se cumpla la regla, `ml_salud/resultados/` no cambia.

## Origen de la hipótesis

Una exploración con validación cruzada solo en entrenamiento mostró que casi toda la ganancia de añadir contexto venía de dos señales derivadas de `P_ENFERMO`. Como la hipótesis salió de esos datos de entrenamiento, la CV aquí no es confirmatoria; la validación separada sí se consulta por primera vez para este candidato. Las definiciones finales difieren en un punto de las exploradas: la sección excluye al hogar de la persona.

## Candidato único

Boosting de histogramas con los parámetros publicados (tasa 0,04, 31 hojas, mínimo 30 por hoja, 320 iteraciones) y las 26 variables actuales más:

- `HOGAR_OTROS_ENFERMOS`: otras personas del mismo hogar con `P_ENFERMO=1`.
- `SECCION_PCT_ENFERMOS`: proporción con `P_ENFERMO=1` entre las personas de la misma sección censal fuera del hogar, con respuesta válida (1 o 2). Queda vacía si no hay ninguna.

La sección se obtiene de `CNPV2018_MGN_A2_08.CSV`. Ninguna de las dos usa `P_QUEHIZO_PPAL`, `PA_LO_ATENDIERON` ni la etiqueta. No se prueban otras variables ni parámetros en esta ronda.

## Regla de adopción

El candidato se adopta solo si cumple **todas** estas condiciones frente al modelo de 26 variables:

1. Ganancia de AP en validación de al menos 0,010.
2. Intervalo percentil 95 % de esa diferencia, por bootstrap pareado de viviendas (semilla 44, 250 réplicas), enteramente por encima de cero.
3. Brier de validación que no empeore más de 0,002.
4. Ganancia media de AP de al menos 0,010 en CV de 3 pliegues dentro de entrenamiento con **secciones no vistas**. Evita premiar la memoria del barrio.
5. Sensibilidad en validación del grupo con dificultad funcional que no caiga más de 0,03, cada modelo con su umbral F1 elegido en validación.

Si alguna falla, se conserva el modelo actual y el hallazgo queda documentado.

## Si se adopta

1. El modelo de 26 variables se archiva en `ml_salud/resultados_v1/` sin alterarlo.
2. `python -m ml_salud.entrenar` repite con 28 variables el protocolo completo: los mismos cuatro enfoques, la misma búsqueda y la selección en validación.
3. La prueba se consulta **una sola vez**, al final de ese proceso. Ya fue observada con el modelo anterior, así que sigue siendo una evaluación interna y no confirmatoria.

## Límites declarados de antemano

- Ambas variables se miden en el mismo censo que la respuesta. No revelan la acción de la persona, pero no son anteriores al episodio.
- La proporción por sección varía más de lo que cabría esperar solo por morbilidad. Puede reflejar problemas más leves, quién respondió o cómo se recogió el dato. El censo no permite separar esas explicaciones.
- Mejorar el AP no convierte la etiqueta en una medida de barreras ni autoriza decisiones sobre personas.
