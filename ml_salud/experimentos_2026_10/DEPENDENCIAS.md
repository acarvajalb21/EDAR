# Comprobación de bibliotecas opcionales

El 27 de octubre de 2026, el entorno local `.venv` usaba Python 3.14.6, NumPy 2.5.2, pandas 3.0.5 y scikit-learn 1.9.1. `importlib.util.find_spec` devolvió `False` para `catboost`, `lightgbm` y `xgboost`.

Se intentó comprobar disponibilidad de paquetes binarios sin instalar nada:

```powershell
.\.venv\Scripts\python.exe -m pip install --dry-run --only-binary=:all: catboost lightgbm xgboost
```

La conexión a `pypi.org:443` falló con `WinError 10013` (acceso de socket no permitido). El comando acabó con código 1. Esta comprobación **no demuestra** incompatibilidad de esas bibliotecas con Python 3.14; solo registra que no pudieron obtenerse en esta sesión. No se asignan resultados predictivos a modelos que no se ejecutaron.
