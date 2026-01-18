#!/usr/bin/env python3
"""dojo_passgen.py

E-T-KDF v4.2 (ALFANUMERICO PURO) + MODO SEGURO + REVELAR CON CONFIRMACION + COPIAR AL PORTAPAPELES

- NO imprime passwords por defecto (solo fingerprints).
- SHOW requiere confirmacion OK/SI antes de mostrar.
- COPY copia al portapapeles sin imprimir la clave (muestra solo fingerprint).

Modos:
- ROT: rotacion mensual (mezcla temporal) -> cambia "por todo" cada mes.
- FIX: fijo (sin rotacion) -> estable para sitios donde rotar es impractico.

Salidas disponibles:
- PRINCIPAL (12)
- EXPRESS (10)
- EMERGENCIA (8)

Seguridad operacional:
- Evita ejecutar en entornos compartidos (repl/colab/notebooks compartidos).
- Evita compartir pantalla cuando uses SHOW.
"""

from __future__ import annotations

from datetime import datetime
from getpass import getpass
import hashlib
import os
import re
import subprocess
import sys

VOWEL_MAP = str.maketrans({"a": "4", "e": "3", "i": "1", "o": "0", "u": "U"})
ALNUM_RE = re.compile(r"^[A-Za-z0-9]+$")

BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
BASE62_INDEX = {c: i for i, c in enumerate(BASE62)}


# -------------------------
# Clipboard utilities
# -------------------------

def _try_run(cmd: list[str], input_text: str) -> bool:
    try:
        subprocess.run(cmd, input=input_text.encode("utf-8"), check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except Exception:
        return False


def copy_to_clipboard(text: str) -> tuple[bool, str]:
    """Best-effort clipboard copy without external Python deps.

    Returns: (ok, method)
    """
    plat = sys.platform

    # macOS
    if plat == "darwin":
        if _try_run(["pbcopy"], text):
            return True, "pbcopy"
        return False, "pbcopy (no disponible)"

    # Windows
    if plat.startswith("win"):
        # 'clip' is a shell built-in in many environments; calling via cmd works
        if _try_run(["cmd", "/c", "clip"], text):
            return True, "clip"
        return False, "clip (no disponible)"

    # Linux / *nix
    # Prefer xclip, fallback xsel
    if _try_run(["xclip", "-selection", "clipboard"], text):
        return True, "xclip"
    if _try_run(["xsel", "--clipboard", "--input"], text):
        return True, "xsel"

    return False, "xclip/xsel (no disponible)"


# -------------------------
# Core derivation
# -------------------------

def read_lines(prompt: str) -> list[str]:
    print(prompt)
    out: list[str] = []
    while True:
        line = input().strip()
        if not line:
            break
        out.append(line)
    return out


def split_email(email: str) -> tuple[str, str]:
    email = email.strip()
    if "@" not in email:
        return (email, "")
    alias, dom = email.split("@", 1)
    return alias.strip(), dom.strip()


def normalize_alias(alias: str) -> str:
    alias = alias.strip().lower()
    alias = re.sub(r"\d+", "", alias)
    alias = re.sub(r"[^a-z]", "", alias)
    return alias


def pick_first_middle_last(s: str) -> str:
    if len(s) < 3:
        raise ValueError("El alias quedo muy corto tras limpieza (sin numeros y solo letras).")
    first = s[0]
    mid = s[len(s) // 2]
    last = s[-1]
    return (first + mid + last).translate(VOWEL_MAP)


def derive_kr_base(email: str, sh: str) -> str:
    alias, _ = split_email(email)
    base3 = pick_first_middle_last(normalize_alias(alias))  # 3
    kr = base3[0] + sh + base3[1:]  # 6
    if len(kr) != 6 or not ALNUM_RE.match(kr):
        raise ValueError("KR_base invalida. Revisa SH (3 alfanumericos).")
    return kr


def normalize_site_domain(site_domain: str) -> str:
    d = site_domain.strip().lower()
    d = d.replace("https://", "").replace("http://", "")
    d = d.split("/", 1)[0].split(":", 1)[0]
    if not d:
        raise ValueError("Dominio del sitio vacio.")
    label = d.split(".", 1)[0]
    label = re.sub(r"[^a-z]", "", label)
    if len(label) < 3:
        raise ValueError(f"Dominio de sitio demasiado corto tras limpieza: '{label}'")
    return label


def site_code_base(site_domain: str) -> str:
    base = normalize_site_domain(site_domain)
    second = base[1]
    penult = base[-2]
    length_digit = str(len(base) % 10)
    sc = (second + penult + length_digit).translate(VOWEL_MAP)
    if len(sc) != 3 or not ALNUM_RE.match(sc):
        raise ValueError("SiteCode_base invalido (no deberia pasar).")
    return sc


def time_code_3(month: int, year: int) -> str:
    val = (month * 3) + (year % 100)
    return f"{val:03d}"


def base62_shift_char(c: str, k: int) -> str:
    if c not in BASE62_INDEX:
        raise ValueError("Caracter no base62 (no deberia pasar).")
    return BASE62[(BASE62_INDEX[c] + k) % 62]


def mix_rot(kr6: str, sc3: str, tc3: str) -> str:
    a, b, c = (int(tc3[0]), int(tc3[1]), int(tc3[2]))
    seed = a + 2 * b + 3 * c
    raw12 = kr6 + sc3 + tc3

    mixed = []
    for i, ch in enumerate(raw12):
        k = (seed + i + a * (i % 3) + b * (i % 5) + c * (i % 7)) % 62
        mixed.append(base62_shift_char(ch, k))
    s = "".join(mixed)

    rot = (seed + a + b + c) % 12
    return s[rot:] + s[:rot]


def mix_fix(kr6: str, sc3: str) -> str:
    raw9 = kr6 + sc3
    digest = hashlib.sha256(raw9.encode("utf-8")).digest()

    tail = [BASE62[digest[i] % 62] for i in range(3)]
    raw12 = raw9 + "".join(tail)

    seed = sum(BASE62_INDEX[ch] for ch in tail) % 62
    mixed = []
    for i, ch in enumerate(raw12):
        k = (seed + i * 7) % 62
        mixed.append(base62_shift_char(ch, k))

    rot = seed % 12
    s = "".join(mixed)
    return s[rot:] + s[:rot]


def pwd_principal_rot(email: str, sh: str, site_domain: str, month: int, year: int) -> str:
    kr = derive_kr_base(email, sh)
    sc = site_code_base(site_domain)
    tc = time_code_3(month, year)
    pwd = mix_rot(kr, sc, tc)
    if len(pwd) != 12 or not ALNUM_RE.match(pwd):
        raise ValueError("Principal ROT invalida.")
    return pwd


def pwd_principal_fix(email: str, sh: str, site_domain: str) -> str:
    kr = derive_kr_base(email, sh)
    sc = site_code_base(site_domain)
    pwd = mix_fix(kr, sc)
    if len(pwd) != 12 or not ALNUM_RE.match(pwd):
        raise ValueError("Principal FIX invalida.")
    return pwd


def pwd_express(email: str, sh: str, site_domain: str, month: int, year: int) -> str:
    kr = derive_kr_base(email, sh)
    sc2 = site_code_base(site_domain)[:2]
    yd = str(year % 10)
    pwd = f"{kr}{sc2}{month}{yd}"
    if len(pwd) != 10 or not ALNUM_RE.match(pwd):
        raise ValueError("Express invalida.")
    return pwd


def pwd_emergency(email: str, sh: str, month: int, year: int) -> str:
    kr = derive_kr_base(email, sh)
    yd = str(year % 10)
    pwd = f"{kr}{month}{yd}"
    if len(pwd) != 8 or not ALNUM_RE.match(pwd):
        raise ValueError("Emergencia invalida.")
    return pwd


def fingerprint(pwd: str) -> str:
    return hashlib.sha256(pwd.encode("utf-8")).hexdigest()[:10]


# -------------------------
# UI / Commands
# -------------------------

def show_help():
    print(
        """
Comandos:
  LIST
      Lista emails cargados

  FP <email>
      Muestra fingerprints (ROT y FIX)

  SHOW <email> [ROT|FIX]
      Revela en pantalla (requiere confirmacion OK/SI)

  COPY <email> [ROT|FIX] [PRINCIPAL|EXPRESS|EMERGENCIA]
      Copia al portapapeles SIN imprimir la clave (muestra solo fingerprint).
      Por defecto: ROT PRINCIPAL

  HELP
  EXIT

Notas:
- ROT depende de mes/anio y cambia casi todo cada mes.
- FIX es estable (sin rotacion) para sitios legacy.
""".strip()
    )


def confirm_reveal(email: str, mode: str) -> bool:
    print(f"Vas a revelar una contrasena en pantalla para: {email} (modo {mode}).")
    ans = input("Escribe OK para continuar (o Enter para cancelar): ").strip().upper()
    return ans in ("OK", "SI", "SÍ")


def compute_bundle(email: str, sh: str, site_dom: str, month: int, year: int, mode: str) -> dict[str, str]:
    mode = mode.upper()
    if mode == "ROT":
        principal = pwd_principal_rot(email, sh, site_dom, month, year)
    elif mode == "FIX":
        principal = pwd_principal_fix(email, sh, site_dom)
    else:
        raise ValueError("Modo invalido. Usa ROT o FIX.")

    express = pwd_express(email, sh, site_dom, month, year)
    emerg = pwd_emergency(email, sh, month, year)

    return {
        "PRINCIPAL": principal,
        "EXPRESS": express,
        "EMERGENCIA": emerg,
        "FP": fingerprint(principal),
    }


def main():
    emails = read_lines("Pega tus emails (uno por linea). Linea vacia para terminar:")
    if not emails:
        print("No ingresaste emails. Saliendo.")
        return

    site_dom = input("Dominio del SITIO (ej: github.com, Enter=gmail.com): ").strip() or "gmail.com"

    while True:
        sh = getpass("Secreto Humano (SH) de 3 caracteres alfanumericos (no se muestra): ").strip()
        if len(sh) == 3 and ALNUM_RE.match(sh):
            break
        print("SH invalido. Debe ser EXACTAMENTE 3 caracteres y solo letras/numeros. Ej: Q7X")

    now = datetime.now()
    raw_m = input(f"Mes [1-12] (Enter={now.month}): ").strip()
    raw_y = input(f"Anio (Enter={now.year}): ").strip()
    month = int(raw_m) if raw_m else now.month
    year = int(raw_y) if raw_y else now.year
    if not (1 <= month <= 12):
        raise ValueError("Mes invalido.")

    sc_dbg = site_code_base(site_dom)
    tc_dbg = time_code_3(month, year)

    fps: dict[str, dict[str, str]] = {}
    email_set = {e.strip(): True for e in emails}

    print("\n=== MODO SEGURO: SOLO HUELLAS (NO PASSWORDS) ===")
    print(f"Sitio: {site_dom} | SiteCode: {sc_dbg} | Fecha: {month:02d}/{year} | TimeCode: {tc_dbg}")
    print("-" * 90)

    for e in emails:
        try:
            rot = pwd_principal_rot(e, sh, site_dom, month, year)
            fix = pwd_principal_fix(e, sh, site_dom)
            fps[e] = {"ROT": fingerprint(rot), "FIX": fingerprint(fix)}
            print(f"Email: {e}")
            print(f"  FP ROT(12): {fps[e]['ROT']}")
            print(f"  FP FIX(12): {fps[e]['FIX']}")
            print("-" * 90)
        except Exception as ex:
            print(f"Email: {e}\n  ERROR: {ex}\n" + "-" * 90)

    print("Comandos: HELP | LIST | FP <email> | SHOW <email> ROT|FIX | COPY <email> ROT|FIX PRINCIPAL|EXPRESS|EMERGENCIA | EXIT\n")

    while True:
        cmd = input("> ").strip()
        if not cmd:
            continue

        parts = cmd.split()
        op = parts[0].upper()

        if op in ("EXIT", "QUIT", "SALIR"):
            print("Saliendo.")
            return

        if op == "HELP":
            show_help()
            continue

        if op == "LIST":
            for e in emails:
                print(e)
            continue

        if op == "FP":
            if len(parts) < 2:
                print("Uso: FP <email>")
                continue
            e = " ".join(parts[1:]).strip()
            if e not in fps:
                print("Email no encontrado en la lista.")
                continue
            print(f"Email: {e}")
            print(f"  FP ROT(12): {fps[e]['ROT']}")
            print(f"  FP FIX(12): {fps[e]['FIX']}")
            continue

        if op == "SHOW":
            if len(parts) < 2:
                print("Uso: SHOW <email> [ROT|FIX]")
                continue
            e = parts[1].strip()
            mode = parts[2].upper() if len(parts) >= 3 else "ROT"

            if e not in email_set:
                print("Email no encontrado en la lista.")
                continue
            if mode not in ("ROT", "FIX"):
                print("Modo invalido. Usa ROT o FIX.")
                continue

            if not confirm_reveal(e, mode):
                print("Cancelado.")
                continue

            try:
                b = compute_bundle(e, sh, site_dom, month, year, mode)
                print(f"\nEmail: {e} | Modo: {mode}")
                print(f"  PRINCIPAL (12):  {b['PRINCIPAL']}")
                print(f"  EXPRESS (10s):   {b['EXPRESS']}")
                print(f"  EMERGENCIA (8):  {b['EMERGENCIA']}")
                print(f"  Fingerprint:     {b['FP']}\n")
            except Exception as ex:
                print(f"ERROR: {ex}")
            continue

        if op == "COPY":
            if len(parts) < 2:
                print("Uso: COPY <email> [ROT|FIX] [PRINCIPAL|EXPRESS|EMERGENCIA]")
                continue

            e = parts[1].strip()
            mode = parts[2].upper() if len(parts) >= 3 else "ROT"
            which = parts[3].upper() if len(parts) >= 4 else "PRINCIPAL"

            if e not in email_set:
                print("Email no encontrado en la lista.")
                continue
            if mode not in ("ROT", "FIX"):
                print("Modo invalido. Usa ROT o FIX.")
                continue
            if which not in ("PRINCIPAL", "EXPRESS", "EMERGENCIA"):
                print("Salida invalida. Usa PRINCIPAL, EXPRESS o EMERGENCIA.")
                continue

            try:
                b = compute_bundle(e, sh, site_dom, month, year, mode)
                secret = b[which]
                ok, method = copy_to_clipboard(secret)
                if ok:
                    print(f"OK: copiado al portapapeles ({method}). Email={e} modo={mode} salida={which} FP={b['FP']}")
                else:
                    print(f"No se pudo copiar al portapapeles ({method}).\nPor seguridad, NO imprimire la clave.\nSugerencia: instala xclip/xsel (Linux) o usa SHOW con precaucion.")
            except Exception as ex:
                print(f"ERROR: {ex}")
            continue

        print("Comando no reconocido. Escribe HELP.")


if __name__ == "__main__":
    main()
