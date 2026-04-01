# 📜 Spécifications (V1 - Simulation Python)

## 1. Vision du Projet
Visualiseur audio temps réel. Il transforme l'entrée microphone en un flux de données visuelles réparti sur 4 rubans LED (virtuels en V1). L'effet principal est un "serpent" (propagation) où chaque nouvelle analyse audio pousse les anciennes valeurs vers le bout du ruban.

---

## 2. Spécifications Fonctionnelles

### 2.1 Capture Audio & Analyse
* **Source :** Flux micro continu (Mono, 44.1/48kHz).
* **Bandes de fréquences :** Décomposition du spectre en 4 canaux :
  1. **Basses :** 20 - 250 Hz (Percussions, Kick).
  2. **Mids :** 250 - 2000 Hz (Instruments, Accords).
  3. **High-Mids :** 2000 - 6000 Hz (Vocaux, Lead).
  4. **Highs :** 6000 - 20000 Hz (FX, Cymbale, Air).
* **Normalisation (AGC) :** Un algorithme d'Auto-Gain Control doit ajuster l'amplitude en temps réel pour que les LEDs restent réactives même si le volume d'entrée est faible.

### 2.2 Algorithme "Snake" (Propagation)
* **Comportement :** À chaque intervalle défini par le `TICK_RATE`, la couleur de la LED $i$ devient celle de la LED $i-1$.
* **Génération (LED 0) :** La première LED de chaque bande est calculée selon :
  - **Teinte (Hue) :** Basée sur la fréquence dominante au sein de la bande (Gradient continu).
  - **Luminosité (Value) :** Basée sur l'amplitude (volume) du canal.
* **Palette :** Transition fluide du Bleu/Rouge (Grave) vers le Turquoise/Blanc (Aigu).

### 2.3 Interface Utilisateur (V1)
* **Visualisation :** 4 rubans horizontaux simulant des LEDs WS2812B.
* **Contrôle Tempo :**
  - Un champ de saisie numérique (BPM).
  - Un bouton "Valider" pour mettre à jour le `TICK_RATE` à la volée.
  - Formule : $Tick\_Rate (ms) = \frac{60000}{BPM \times Multiplicateur}$ (par défaut, 1 tick par temps ou subdivision).

---

## 3. Architecture Technique

### 3.1 Stack Logicielle
- **Langage :** Python 3.11+.
- **Traitement Signal :** `Numpy`, `Scipy.fft`.
- **Audio :** `PyAudio` (Capture temps réel).
- **Graphismes :** `Pygame` (Simulation 60 FPS).

### 3.2 Structure Modulaire
1. **`AudioAnalyzer` :** Capture le flux, applique la FFT, calcule l'énergie par bande et gère l'AGC.
2. **`SnakeEngine` :** Gère les 4 buffers (`collections.deque`) et la logique de décalage.
3. **`Mapper` :** Convertit les données audio (Freq/Amp) en valeurs RGB/HSV.
4. **`Display` :** Interface Pygame pour le rendu et le contrôle BPM.

---

## 4. Roadmap & Évolutions
- **V2 :** Envoi des données via UDP vers un ESP32 (Physical LED Drive).
- **V3 :** Détection automatique de BPM (Beat Detection).
- **V4 :** Stemming IA (Spleeter/Demucs) pour une séparation parfaite des voix.
- **V5 :** Portage intégral en C (ESP-IDF) pour exécution autonome sur ESP32.