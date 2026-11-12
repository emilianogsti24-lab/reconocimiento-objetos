# Reconocimiento de objetos

Interfaz web local para clasificar imágenes de la cámara usando el modelo de
Teachable Machine incluido en `tm-my-image-model.zip`.

Clases incluidas: **Libros**, **Lentes** y **Extintores**.

## Requisitos

- Python 3.9 o posterior
- Un navegador con permiso para acceder a la cámara
- Conexión a Internet para cargar TensorFlow.js desde jsDelivr

## Ejecutar

Desde esta carpeta, inicia el servidor:

```bash
python3 PROGRECONOCIMIENTOCAMARA.py
```

Abre <http://127.0.0.1:8000>, pulsa **Activar cámara** y concede el permiso
cuando el navegador lo solicite.

El conteo suma una aparición cuando una clase supera el 80 % de confianza y
vuelve a aparecer después de dejar de detectarse. El modelo clasifica la imagen
completa; no genera recuadros ni distingue varias unidades de la misma clase
simultáneamente.
