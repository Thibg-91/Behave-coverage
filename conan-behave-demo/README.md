# conan-behave-demo

Mini-projet illustrant l'intégration entre **Conan 2** et **Behave** :
un test BDD, exécuté par des steps Python, déclenche lui-même la
création du package Conan (installation dans le cache local), puis
consomme ce package **directement depuis le cache** en générant un
script d'environnement Conan (**VirtualRunEnv** → `conanrun.sh`) —
sans rien recompiler ni relinker côté consommateur.

## Structure

```
conan-behave-demo/
├── package/                        # Recette Conan 2 du package "mathutils"
│   ├── conanfile.py
│   ├── CMakeLists.txt
│   ├── include/mathutils/mathutils.hpp
│   └── src/
│       ├── mathutils.cpp           # libmathutils.so
│       └── mathutils_cli.cpp       # exécutable mathutils-cli (lié à la lib)
├── tests/
│   ├── behave.ini
│   └── features/
│       ├── conan_package.feature
│       └── steps/
│           └── conan_steps.py      # Les steps appellent réellement `conan`
└── requirements.txt
```

Le package `mathutils` embarque volontairement **une librairie
partagée** (`libmathutils.so`) **et un exécutable** (`mathutils-cli`)
qui en dépend, sans rpath (le `CMakeLists.txt` ne configure aucun
rpath d'installation). Résultat : lancer `mathutils-cli` directement
depuis le dossier du package en cache échoue (`libmathutils.so:
cannot open shared object file`), sauf si `LD_LIBRARY_PATH` /
`PATH` sont positionnés correctement — exactement ce que fait le
générateur Conan **VirtualRunEnv**.

## Ce que fait le test

Le fichier `tests/features/conan_package.feature` définit un
`Background` commun (nettoyage du cache puis `conan create`), suivi
de deux scénarios :

1. **Sans script d'environnement** : on exécute `mathutils-cli`
   directement depuis son dossier dans le cache Conan → le test
   vérifie que ça échoue bien faute de `libmathutils.so` trouvable.
   Ça prouve que la lib n'est pas magiquement accessible.
2. **Avec le script VirtualRunEnv** : le step
   `When I generate the Conan virtual run environment for
   "mathutils/1.0.0"` exécute :

   ```bash
   conan install --requires=mathutils/1.0.0 --no-remote \
       -g VirtualRunEnv --output-folder=<tmp>
   ```

   ce qui génère `conanrun.sh` (et son fichier d'environnement
   associé) dans un dossier temporaire — **sans télécharger ni
   reconstruire quoi que ce soit**, le package est déjà en cache.
   Le step suivant source ce script puis invoque `mathutils-cli`,
   trouvé via le `PATH` exporté, et vérifie sa sortie.

C'est donc bien un test Behave qui, via ses steps Python : (1) déclenche
la création + l'installation du package en cache (`conan create`), puis
(2) génère et utilise le script `VirtualRunEnv` pour consommer ce même
package directement depuis le cache.

## Prérequis

| Outil  | Version |
|--------|---------|
| Python | 3.8+    |
| Conan  | 2.x     |
| CMake  | 3.16+   |
| Un compilateur C++17 (gcc/clang) | — |

```bash
pip install -r requirements.txt

# Une seule fois par machine : détecter un profil Conan par défaut
conan profile detect --force
```

> `mathutils` n'a aucune dépendance externe : toutes les commandes Conan
> utilisées ici passent `--no-remote` pour rester 100% locales (pas besoin
> d'accès à conancenter, utile en environnement restreint/hors-ligne).

## Lancer le test

```bash
cd conan-behave-demo/tests
behave
```

Le `Background` nettoie d'abord le cache Conan (`conan remove -c
mathutils/1.0.0`), pour garantir que c'est bien le test lui-même qui
provoque la (re)création du package avant de le consommer.

## Exécuter les étapes manuellement (debug)

```bash
# 1. Créer et installer le package en cache
conan create conan-behave-demo/package --build=missing --no-remote

# 2. Vérifier sa présence en cache
conan list "mathutils/1.0.0:*"

# 3. Générer le script VirtualRunEnv pour le consommer depuis le cache
conan install --requires=mathutils/1.0.0 --no-remote \
    -g VirtualRunEnv --output-folder=/tmp/mathutils-env

# 4. Sourcer le script et lancer l'outil, résolu via PATH depuis le cache
source /tmp/mathutils-env/conanrun.sh
mathutils-cli 2 3
```
