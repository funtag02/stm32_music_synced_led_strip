# Copilot Instructions — LuminaSnake

## 🧠 Contexte du Projet

**LuminaSnake** est un **visualiseur audio temps réel** qui transforme un flux microphone en effets visuels sur des rubans LED WS2812B.
L'effet principal est un **"serpent" (snake/propagation)** : chaque nouvelle analyse audio pousse les anciennes valeurs vers le bout du ruban.

Le développement est **itératif et versionné** :

| Version | Description | Stack |
|---------|-------------|-------|
| V1 | Simulation Python (PC) | Python, Pygame, NumPy, PyAudio |
| V2 | Envoi UDP → ESP32 (LEDs physiques) | Python (émetteur) + C/ESP-IDF (récepteur) |
| V3 | Détection automatique BPM | Python + embarqué |
| V4 | Stemming IA (Spleeter/Demucs) | Python, ML |
| V5 | Portage intégral C, autonome sur ESP32 | C, ESP-IDF |

---

## 👤 Profil Développeur

- **Python** : Niveau expert. Ne pas simplifier inutilement la logique Python.
- **Embarqué (C, ESP-IDF, PlatformIO)** : Niveau débutant.
  - ⚠️ **Toujours expliquer** les concepts embarqués : registres, DMA, timers, périphériques, protocoles (I2S, SPI, RMT, UART, UDP...).
  - Justifier chaque choix d'architecture bas niveau (pourquoi DMA plutôt que polling, pourquoi RMT pour WS2812B, etc.).
  - Fournir des analogies avec Python quand c'est pertinent.

---

## 🐍 Conventions Python

### Style général
- **Docstrings** : obligatoires sur chaque classe, méthode et fonction (format Google Style ou NumPy Style).
- **Commentaires inline** : détaillés, expliquer le *pourquoi* pas seulement le *quoi*.
- **Type hints** : utilisés uniquement quand ils apportent de la clarté (signatures de fonctions publiques).
- **PEP8** : respecté strictement.
- Privilégier la lisibilité à la concision.

### Structure du projet (V1)
```
led_visualizer/
├── main.py               # Point d'entrée
├── audio_analyzer.py     # Capture + FFT + AGC
├── snake_engine.py       # Buffers deque + logique de décalage
├── mapper.py             # Conversion audio → RGB/HSV
├── display.py            # Rendu Pygame + UI BPM
└── config.py             # Constantes globales (TICK_RATE, bandes, couleurs...)
```

### Modules clés
- `AudioAnalyzer` : PyAudio + NumPy FFT + AGC (Auto-Gain Control)
  - Capture **non-bloquante** (callback PyAudio ou thread dédié)
  - Application d'une **fenêtre de Hanning** sur chaque buffer avant FFT
  - Extraction amplitude RMS + fréquence dominante par bande
  - Gestion des erreurs périphériques (micro non trouvé, sample rate incompatible)
- `SnakeEngine` : 4x `collections.deque`, logique snake tick-based
- `Mapper` : Conversion énergie par bande → HSV → RGB
- `Display` : Pygame 60 FPS, **4 rubans de 60 LEDs** horizontaux, contrôle BPM

### Abstraction pour la V2 (ABCs)
Les modules `Display` et l'émetteur de données doivent reposer sur des **classes abstraites** (`abc.ABC`) afin de pouvoir remplacer le rendu Pygame par un émetteur UDP sans modifier le reste du code.

```python
# Exemple de contrat abstrait
class BaseRenderer(ABC):
    @abstractmethod
    def render(self, strips: list[list[tuple[int, int, int]]]) -> None: ...

    @abstractmethod
    def handle_events(self) -> dict: ...
```

---

## 🎛️ Paramètres Audio

| Paramètre | Valeur |
|-----------|--------|
| Sample Rate | 44100 ou 48000 Hz |
| Canaux | Mono |
| Bandes | 4 (Basses / Mids / High-Mids / Highs) |

### Bandes de fréquences
| # | Nom | Plage | Couleur dominante |
|---|-----|-------|-------------------|
| 1 | Basses | 20 – 250 Hz | Bleu / Rouge profond |
| 2 | Mids | 250 – 2000 Hz | Violet / Magenta |
| 3 | High-Mids | 2000 – 6000 Hz | Vert / Cyan |
| 4 | Highs | 6000 – 20000 Hz | Turquoise / Blanc |

---

## 💡 Algorithme Snake

- À chaque **tick** (cadencé par le BPM), la LED `i` prend la couleur de la LED `i-1`.
- La **LED 0** est générée à partir de l'analyse audio courante :
  - **Hue** : fréquence dominante dans la bande (gradient continu)
  - **Value** : amplitude (volume) du canal
- Formule du tick rate : `TickRate(ms) = 60000 / (BPM × multiplicateur)`

---

## ⚡ Contraintes de Performance & Robustesse

- **FFT** : calculs entièrement vectorisés avec NumPy — pas de boucles Python sur les échantillons.
- **Capture audio** : non-bloquante (callback PyAudio ou thread) pour ne jamais bloquer la boucle Pygame.
- **Framerate Pygame** : stable à 60 FPS, **indépendant** du tick rate audio.
- **Gestion d'erreurs audio** : micro non trouvé, sample rate non supporté, buffer underrun → logger l'erreur et continuer proprement.
- **Pas de stemming IA en V1** : uniquement FFT + bandes de fréquences.

---



- **Éditeur** : VS Code
- **Python** : 3.11+
- **Embarqué** : PlatformIO (extension VS Code) — supporte ESP32 et STM32 dans le même environnement
- **Cible matérielle principale** : ESP32 (WiFi natif, RMT pour WS2812B)
- **Cible alternative** : STM32H750 (si traitement audio embarqué nécessaire en V5)

---

## 📡 Architecture Réseau (V2+)

- **Protocole** : UDP (faible latence, tolérance aux pertes acceptée pour du visuel)
- **Émetteur** : PC Python → socket UDP
- **Récepteur** : ESP32 → parse le paquet → pilote les LEDs via RMT

---

## ⚠️ Règles pour l'IA

1. **Ne jamais supposer** que le développeur connaît un concept embarqué — toujours l'expliquer.
2. **Toujours commenter** le code C/C++ ligne par ligne ou bloc par bloc.
3. En Python, écrire du code **idiomatique et expert** (dataclasses, ABCs, générateurs, etc. si pertinent).
4. Respecter la **structure modulaire** définie ci-dessus — ne pas tout mettre dans `main.py`.
5. Pour chaque nouvelle version, **rappeler les dépendances** à installer et la commande de lancement.
6. Si un choix d'architecture a des **alternatives**, les mentionner brièvement avec les trade-offs.
7. Les **constantes globales** vont dans `config.py` — ne pas les hardcoder dans les modules.
8. Langue du code : **anglais** (noms de variables, commentaires, docstrings).
9. Langue des échanges : **français**.