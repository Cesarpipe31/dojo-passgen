# dojo-passgen — E-T-KDF v4.2 (12 caracteres alfanuméricos) + modo seguro

Generador determinista de contraseñas **alfanuméricas** (sin apps) basado en:
- **Email** (identidad / cuenta)
- **Dominio del sitio** (contexto: github.com, google.com, etc.)
- **Tiempo** (mes/año) para rotación mensual (**ROT**)
- Modo estable (**FIX**) para sitios donde rotar es impráctico

Incluye:
- **Modo seguro por defecto**: NO imprime contraseñas, solo **fingerprints** (huellas)
- `SHOW` con confirmación **OK/SI** para revelar una clave puntual
- `COPY` para **copiar al portapapeles** sin imprimir la clave

> ⚠️ Importante
> - Esto NO sustituye un gestor aleatorio “de bóveda”.
> - Es un sistema determinista para escenarios “sin app”.
> - Activa **2FA** siempre que puedas.

---

## Requisitos

- Python 3.8+ (recomendado 3.10+)
- Sin dependencias externas (solo librería estándar)

### Portapapeles (opcional)

- **macOS**: viene listo (`pbcopy`)
- **Windows**: viene listo (`clip`)
- **Linux**: instala **xclip** o **xsel**
  - Debian/Ubuntu: `sudo apt-get install xclip`
  - Fedora: `sudo dnf install xclip`

---

## Uso rápido

```bash
python3 dojo_passgen.py
```

1) Pega tus emails (uno por línea). Línea vacía para terminar.
2) Escribe el **dominio del sitio** (ej: `github.com`).
3) Ingresa tu **Secreto Humano (SH)** de 3 caracteres alfanuméricos (no se muestra).
4) (Opcional) mes/año. Enter usa el actual.

El programa mostrará **solo fingerprints** por defecto.

---

## ROT vs FIX

- **ROT**: contraseña “viva” (cambia por mes/año y se mezcla para que no cambien solo 3 caracteres).
  - Úsalo para correo, bancos, GitHub, cloud, trabajo.

- **FIX**: contraseña estable (no depende del tiempo).
  - Úsalo para sitios legacy o donde cambiar es doloroso.

Regla rápida:
- *Si la caída te quita el sueño → ROT*
- *Si la caída es tolerable → FIX*

---

## Comandos

Dentro del programa:

- `LIST`
  - Lista emails cargados

- `FP <email>`
  - Muestra fingerprints (ROT y FIX)

- `SHOW <email> [ROT|FIX]`
  - Revela en pantalla (requiere confirmación OK/SI)

- `COPY <email> [ROT|FIX] [PRINCIPAL|EXPRESS|EMERGENCIA]`
  - Copia al portapapeles sin imprimir la clave
  - Por defecto: `ROT PRINCIPAL`

- `HELP`
- `EXIT`

---

## Buenas prácticas

- No publiques tu SH.
- Evita ejecutar el script en entornos compartidos.
- Evita compartir pantalla cuando uses `SHOW`.
- Usa `COPY` cuando sea posible.
- Activa 2FA.

---

## Licencia

MIT (ver `LICENSE`).
