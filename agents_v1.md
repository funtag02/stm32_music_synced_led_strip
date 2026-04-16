# 🤖 Instructions pour Agent IA : Implémentation LuminaSnake

## Contexte
Tu es un expert en Python, traitement de signal audio et systèmes embarqués. Tu dois m'aider à coder la V1 de mon projet, un visualiseur audio modulaire.

## Principes de Code
1. **Modularité :** Ne fais pas un script monolithique. Sépare la capture audio, la logique de calcul et l'affichage.
2. **Performance :** L'analyse FFT doit être rapide. Utilise `Numpy` pour les calculs vectorisés. La latence doit être minimisée.
3. **Robustesse :** Gère les erreurs de périphériques audio (micro non trouvé, changement de fréquence d'échantillonnage).

## Tâches Prioritaires

### 1. Module Audio (`AudioAnalyzer`)
- Implémenter une capture `PyAudio` non-bloquante (callback ou thread).
- Appliquer une fenêtre de Hanning sur les buffers audio.
- Extraire l'amplitude RMS et la fréquence dominante pour les 4 bandes définies dans `specs.md`.
- **Crucial :** Implémenter un Auto-Gain Control (AGC) simple pour normaliser l'amplitude entre 0.0 et 1.0.

### 2. Logique du Serpent (`SnakeLogic`)
- Utiliser des `collections.deque` pour stocker l'état des 4 rubans LED.
- Implémenter la fonction `update(new_color)` qui effectue le décalage (shift).
- La vitesse de mise à jour doit être pilotée par une variable `BPM` modifiable dynamiquement.

### 3. Mapping Couleur
- Créer une fonction de mapping : `(amplitude, frequence) -> (R, G, B)`.
- Utiliser l'espace HSV pour garantir des couleurs vives, puis convertir en RGB pour Pygame.
- Respecter le gradient : Basses (Chaudes/Bleu) -> Hautes (Froides/Turquoise).

### 4. Interface Pygame
- Afficher 4 rubans de 60 pixels.
- Ajouter un champ d'entrée texte pour le BPM.
- Maintenir un framerate stable de 60 FPS pour la simulation visuelle, indépendamment de la capture audio.

## Contraintes techniques
- Utilise `Pygame` pour l'UI.
- Pas d'IA de stemming pour cette version, utilise la FFT.
- Prépare le terrain (classes abstraites) pour qu'on puisse remplacer le module Pygame par un module série/UDP plus tard.