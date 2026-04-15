# Guide : deux packages Conan 2 — bibliothèque pré-compilée + exécutable consommateur

## Vue d'ensemble

```
conan-demo/
├── mymath-prebuilt/   # Package 1 : lib statique pré-compilée (aucun build Conan)
│   ├── include/
│   │   └── mymath.h
│   ├── src/
│   │   └── mymath.cpp
│   ├── lib/           # généré par build_library.sh
│   │   └── libmymath.a
│   ├── build_library.sh
│   └── conanfile.py
├── myapp/             # Package 2 : exécutable qui consomme mymath
│   ├── src/
│   │   └── main.cpp
│   ├── CMakeLists.txt
│   └── conanfile.py
└── GUIDE.md
```

---

## Prérequis

| Outil | Version minimale |
|-------|-----------------|
| Conan | 2.x (`pip install conan`) |
| CMake | 3.15 |
| GCC / Clang | C++17 |

Vérifiez que Conan est configuré avec un profil par défaut :

```bash
conan profile detect   # crée ~/.conan2/profiles/default si absent
```

---

## Étape 1 — Compiler la bibliothèque manuellement

Le package `mymath` distribue des **binaires pré-compilés** : Conan ne lancera
aucun compilateur. Vous devez donc construire la bibliothèque vous-même avant
de l'empaqueter.

```bash
cd mymath-prebuilt/
chmod +x build_library.sh
./build_library.sh
```

Ce script fait simplement :

```bash
g++ -std=c++17 -O2 -I include/ -c src/mymath.cpp -o mymath.o
ar rcs lib/libmymath.a mymath.o
```

Vous devriez obtenir `lib/libmymath.a`.

> **Note production** : en pratique vous compileriez en Debug *et* Release et
> vous empaquèteriez une version par configuration (via plusieurs appels à
> `conan export-pkg` avec des settings différents).

---

## Étape 2 — Empaqueter la bibliothèque dans le cache Conan

La commande `conan export-pkg` exporte la recette **et** exécute `package()`
pour copier les binaires pré-compilés dans le cache local — sans jamais appeler
`build()`.

```bash
cd mymath-prebuilt/

conan export-pkg . \
    --name mymath \
    --version 1.0 \
    -s os=Linux \
    -s arch=x86_64
```

### Que fait `conan export-pkg` ?

1. Exporte `conanfile.py` vers `~/.conan2/p/` (cache local).
2. Appelle `package()` : les fichiers `include/*.h` et `lib/*.a` sont copiés
   dans le dossier du package dans le cache.
3. N'appelle **pas** `build()`.

Vérifiez que le package est bien dans le cache :

```bash
conan list "mymath/1.0:*"
```

---

## Étape 3 — Comprendre le `conanfile.py` de `mymath`

```python
class MymathConan(ConanFile):
    name = "mymath"
    version = "1.0"
    package_type = "static-library"
    settings = "os", "arch"       # pas de compiler/build_type : binaire unique

    # Pas de build() → Conan ne compilera jamais rien

    def package(self):
        copy(self, "*.h",  src=.../include, dst=.../include)
        copy(self, "*.a",  src=.../lib,     dst=.../lib)

    def package_info(self):
        self.cpp_info.libs = ["mymath"]   # nom sans préfixe ni extension
```

Les points clés :

- **Pas de `build()`** : c'est ce qui empêche Conan de recompiler.
- **`settings` minimal** : on ne tracke que `os` et `arch` car on livre un
  seul binaire.
- **`package_info()`** : décrit aux consommateurs comment linker (`-lmymath`,
  dossier `include/`, dossier `lib/`).

---

## Étape 4 — Construire l'exécutable `myapp`

`myapp` est un package Conan classique avec build CMake.

```bash
cd myapp/

# 1. Installer les dépendances et générer les fichiers CMake
conan install . \
    --output-folder=build \
    --build=missing \
    -s build_type=Release

# 2. Configurer CMake avec le toolchain généré par Conan
cmake -S . -B build \
    -DCMAKE_TOOLCHAIN_FILE=build/conan_toolchain.cmake \
    -DCMAKE_BUILD_TYPE=Release

# 3. Compiler
cmake --build build
```

### Résultat attendu

```
[ 50%] Building CXX object CMakeFiles/myapp.dir/src/main.cpp.o
[100%] Linking CXX executable myapp
[100%] Built target myapp
```

---

## Étape 5 — Lancer l'exécutable

```bash
./build/myapp
```

Sortie :

```
7 + 5 = 12
```

---

## Récapitulatif des commandes

```bash
# --- Package 1 : compiler + empaqueter ---
cd mymath-prebuilt/
./build_library.sh
conan export-pkg . --name mymath --version 1.0 -s os=Linux -s arch=x86_64

# Vérification
conan list "mymath/1.0:*"

# --- Package 2 : build + run ---
cd ../myapp/
conan install . --output-folder=build --build=missing -s build_type=Release
cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE=build/conan_toolchain.cmake -DCMAKE_BUILD_TYPE=Release
cmake --build build
./build/myapp
```

---

## Points importants

### Différence entre `conan create` et `conan export-pkg`

| Commande | Compile ? | Usage |
|----------|-----------|-------|
| `conan create` | Oui (appelle `build()`) | Bibliothèque dont on gère les sources dans Conan |
| `conan export-pkg` | Non | Binaires pré-compilés extérieurs à Conan |

### Pourquoi `package_info()` est indispensable

Sans `package_info()`, les consommateurs ne sauraient pas :
- quel fichier `.a` / `.lib` linker (`cpp_info.libs`)
- où chercher les headers (`cpp_info.includedirs`)
- où chercher la bibliothèque (`cpp_info.libdirs`)

Les générateurs Conan (`CMakeDeps`, `CMakeToolchain`) s'appuient sur ces
informations pour générer les fichiers `Find<Package>.cmake` utilisés par CMake.

### Gestion multi-configurations (Debug / Release)

Pour une lib pré-compilée disponible en Debug et Release, compilez les deux
variantes et appelez `export-pkg` deux fois avec des settings différents :

```bash
# Release
./build_library.sh  # compile -O2
conan export-pkg . --name mymath --version 1.0 \
    -s os=Linux -s arch=x86_64

# Debug (recompiler avec -g -O0 puis re-packager)
# g++ -std=c++17 -g -O0 -I include/ -c src/mymath.cpp -o mymath.o && ar rcs lib/libmymath.a mymath.o
# conan export-pkg . --name mymath --version 1.0 \
#     -s os=Linux -s arch=x86_64
```
