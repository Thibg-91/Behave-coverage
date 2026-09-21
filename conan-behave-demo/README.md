# conan-behave-demo

Mini-projet illustrant l'intégration entre **Conan 2** et **Behave** :
un test BDD, exécuté par des steps Python, déclenche lui-même la
création du package Conan et son installation dans le cache local
(`conan create`), puis vérifie que le package est bien présent en
cache et consommable par un autre projet CMake.

## Structure

```
conan-behave-demo/
├── package/                     # Recette Conan 2 de la lib "mathutils"
│   ├── conanfile.py
│   ├── CMakeLists.txt
│   ├── include/mathutils/mathutils.hpp
│   └── src/mathutils.cpp
├── consumer/                    # Projet consommateur du package
│   ├── conanfile.txt
│   ├── CMakeLists.txt
│   └── main.cpp
├── tests/
│   ├── behave.ini
│   └── features/
│       ├── conan_package.feature
│       └── steps/
│           └── conan_steps.py   # Les steps appellent réellement `conan create`
└── requirements.txt
```

## Ce que fait le test

Le fichier `tests/features/conan_package.feature` décrit deux scénarios :

1. **Création du package** : le step `When I run "conan create" on the
   "mathutils/1.0.0" package recipe` construit la lib `mathutils` et
   l'installe dans le cache Conan local (`~/.conan2/p`). Le step suivant
   vérifie via `conan list` que le package s'y trouve bien.
2. **Consommation du package** : un projet CMake indépendant
   (`consumer/`) déclare une dépendance vers `mathutils/1.0.0`. Le test
   exécute `conan install` (qui résout la dépendance depuis le cache
   local rempli à l'étape précédente), configure/compile via les
   *CMake presets* générés par Conan, puis exécute le binaire produit
   et vérifie sa sortie.

C'est donc bien le test Behave lui-même — via ses steps Python — qui
déclenche l'installation du package en cache, pas une étape de build
externe.

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

Chaque exécution nettoie d'abord le cache Conan (`conan remove -c
mathutils/1.0.0`) via le step `Given`, pour garantir que le test part
d'un état propre et que c'est bien lui qui provoque la (re)création du
package.

## Exécuter les étapes manuellement (debug)

```bash
# 1. Créer et installer le package en cache
conan create conan-behave-demo/package --build=missing --no-remote

# 2. Vérifier sa présence en cache
conan list "mathutils/1.0.0:*"

# 3. Consommer le package
cd conan-behave-demo/consumer
conan install . --build=missing --no-remote
cmake --preset conan-release
cmake --build --preset conan-release
./build/Release/mathutils_consumer
```
