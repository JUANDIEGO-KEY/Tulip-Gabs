# tulip-gabs 🌷

Un ramo de tulipanes hecho solo con caracteres de texto. Está escrito en Python
con pygame-ce y corre en la computadora y también en el navegador gracias a
[pygbag](https://github.com/pygame-web/pygbag), que compila el mismo `main.py`
a WebAssembly.

Primero se arma el cono de papel y se amarra el lazo. Después crecen los tallos
y las hojas, salen los botones verdes, se pintan de color desde la punta y los
tulipanes (entre ellos dos rosado claro) se abren uno por uno, rodeados de
racimos de flores no me olvides. Al final aparece un mensaje escrito a máquina.
El ramo se mece con el viento entre luciérnagas, y cada toque en la pantalla
suelta corazones y una ráfaga de aire.

## Verlo en la web

**https://juandiego-key.github.io/Tulip-Gabs/**

Cada vez que se hace push a `main`, GitHub Actions compila la versión web y la
publica en GitHub Pages (`.github/workflows/web.yml`).

El mensaje por defecto es "para ti, feliz cumpleaños, Gaby". Se puede cambiar desde el link, sin tocar el código, con `?msg=`.
Los espacios van como `+`, `|` hace un salto de línea y el corazón es `%E2%99%A5`:

```
https://juandiego-key.github.io/Tulip-Gabs/?msg=feliz+cumple+%E2%99%A5
https://juandiego-key.github.io/Tulip-Gabs/?msg=estos+tulipanes|son+para+ti
```

La fuente incluye letras con tilde y la ñ, pero no emojis.

## Correrlo en la computadora

```
pip install -r requirements.txt
python main.py
python main.py "un mensaje distinto"
```

Teclas: `Espacio` pausa · `R` reinicia · `S` guarda una captura · `Esc` sale.
Clic en cualquier parte para soltar corazones.

Para probar la versión web en tu computadora:

```
pip install pygbag
pygbag --ume_block 0 .
```

y abre http://localhost:8000.

## Cómo está hecho

- **Rejilla de texto:** la pantalla es una rejilla de 80 × 68 celdas. Cada
  elemento (papel, tallos, hojas, flores, lazo) calcula qué celdas ocupa y
  con qué carácter y color; luego se apilan por capas.
- **Formas:** las flores son una función matemática (copa redondeada con tres
  puntas que se separan al abrirse). Los bordes usan `( ) / \ ^ v` según hacia
  dónde va el contorno, y el relleno elige caracteres según el brillo.
- **Animación:** cada parte tiene su momento en una línea de tiempo
  (`T_TISSUE`, `T_STEMS`, `T_BLOOM`, etc. al inicio de `main.py`).
- **Rendimiento:** la escena solo se vuelve a dibujar cuando algo cambia. El
  balanceo mueve franjas horizontales ya dibujadas, así que no cuesta casi nada.
- **Brillo:** una copia borrosa de la escena se suma encima para el efecto de luz.

Los colores, las posiciones de las flores y los tiempos están al inicio de
`main.py` (`SCHEMES`, `TULIPS`, `LEAVES`, `BLOOM_ORDER`, `FORGET_ME_NOTS`).

## Créditos

Inspirado en las animaciones ASCII de
[@dwcminh.ascii](https://instagram.com/dwcminh.ascii). La idea de un ramo que
se arma solo viene de ahí; el código y el diseño de este ramo son originales.

Fuente: DejaVu Sans Mono Bold (licencia en `font/LICENSE-DejaVu.txt`).
