# Guide : deux packages Conan 2 — bibliothèque pré-compilée + exécutable consommateur

## Vue d'ensemble

```
conan-demo/
├── mymath-prebuilt/        # Package 1 : lib statique pré-compilée (aucun build Conan)
│   ├── include/
│   │   └── mymath.h
│   ├── src/
│   │   └── mymath.cpp
│   ├── lib/                # généré par le script de build
│   │   ├── libmymath.a     # Linux / macOS
│   │   └── mymath.lib      # Windows (MSVC)
│   ├── build_library.sh    # Linux / macOS — GCC ou Clang
│   ├── build_library.bat   # Windows — MSVC 2019
│   └── conanfile.py
├── myapp/                  # Package 2 : exécutable qui consomme mymath
│   ├── src/
│   │   └── main.cpp
│   ├── CMakeLists.txt
│   └── conanfile.py
└── GUIDE.md
```

### Cycle de vie des deux packages

```
mymath-prebuilt/                         myapp/
──────────────────────────────           ────────────────────────────────────
1. build_library.sh/.bat                 3. conan create .
   → lib/libmymath.a (ou .lib)              → build() : cmake + compile
                                            → package() : copie bin/myapp
2. conan export-pkg .                       → cache Conan
   → cache Conan (pas de build())
                                         4. conan install --requires myapp/1.0
                                               -g VirtualRunEnv
                                            source conanrun.sh
                                            myapp          ← depuis le cache !
```

---

## Prérequis

| Outil | Version minimale |
|-------|-----------------|
| Conan | 2.x (`pip install conan`) |
| CMake | 3.15 |
| **Linux / macOS** | GCC ≥ 7 ou Clang ≥ 5, C++17 |
| **Windows** | Visual Studio 2019 avec "Développement Desktop en C++" |

Vérifiez que Conan est configuré avec un profil par défaut :

```bash
conan profile detect   # crée ~/.conan2/profiles/default si absent
```

---

## Linux / macOS

### Étape 1 — Compiler `mymath` manuellement

```bash
cd mymath-prebuilt/
chmod +x build_library.sh
./build_library.sh
# → lib/libmymath.a
```

### Étape 2 — Empaqueter `mymath` dans le cache Conan

```bash
conan export-pkg . \
    --name mymath \
    --version 1.0 \
    -s os=Linux \
    -s arch=x86_64
```

> Sur macOS : `-s os=Macos`

```bash
conan list "mymath/1.0:*"   # vérification
```

### Étape 3 — Créer le package `myapp`

`conan create` compile les sources, appelle `package()` pour copier
l'exécutable dans `bin/`, puis place le tout dans le cache Conan.

```bash
cd ../myapp/
conan create . -s build_type=Release
```

Sortie attendue :
```
myapp/1.0: Calling package()
myapp/1.0: package(): Packaged 1 file: myapp
myapp/1.0: Package '...' created
```

### Étape 4 — Consommer et exécuter depuis le package

Depuis n'importe quel dossier (ici `/tmp/run_myapp/`), on demande à Conan
de générer un environnement d'exécution `VirtualRunEnv` qui ajoute le `bin/`
du package à `PATH` :

```bash
mkdir /tmp/run_myapp && cd /tmp/run_myapp

conan install --requires myapp/1.0 \
    -s build_type=Release \
    -g VirtualRunEnv

source conanrun.sh   # injecte le bin/ du cache dans PATH
myapp                # appelle l'exécutable depuis le package Conan
```

Sortie :
```
7 + 5 = 12
```

---

## Windows — MSVC 2019

### Prérequis Windows

- Visual Studio 2019 avec **"Développement Desktop en C++"**
- `vswhere.exe` présent (installé avec Visual Studio)

### Étape 1 — Créer un profil Conan pour MSVC 2019

```bat
conan profile detect
conan profile show
```

Profil attendu :
```ini
[settings]
os=Windows
arch=x86_64
compiler=msvc
compiler.version=192
compiler.runtime=dynamic
compiler.cppstd=14
build_type=Release
```

> `compiler.version=192` = MSVC 14.2x (VS 2019).

### Étape 2 — Compiler `mymath` avec MSVC 2019

```bat
cd mymath-prebuilt\
build_library.bat
:: → lib\mymath.lib
```

Le script localise VS 2019 via `vswhere.exe`, appelle `vcvarsall.bat x64`,
compile avec `cl.exe /std:c++17`, archive avec `lib.exe`.

### Étape 3 — Empaqueter `mymath` dans le cache Conan

```bat
conan export-pkg . ^
    --name mymath ^
    --version 1.0 ^
    -s os=Windows ^
    -s arch=x86_64

conan list "mymath/1.0:*"
```

### Étape 4 — Créer le package `myapp`

```bat
cd ..\myapp\
conan create . -s build_type=Release
```

CMake utilise automatiquement le générateur **Visual Studio 16 2019** détecté
dans le profil Conan. L'exécutable `myapp.exe` est packagé dans `bin/`.

### Étape 5 — Consommer et exécuter depuis le package

```bat
mkdir C:\tmp\run_myapp
cd C:\tmp\run_myapp

conan install --requires myapp/1.0 ^
    -s build_type=Release ^
    -g VirtualRunEnv

call conanrun.bat   :: injecte le bin\ du cache dans PATH
myapp.exe           :: appelle l'exécutable depuis le package Conan
```

---

## Récapitulatif des commandes

### Linux

```bash
# Package 1 — mymath
cd mymath-prebuilt/
./build_library.sh
conan export-pkg . --name mymath --version 1.0 -s os=Linux -s arch=x86_64

# Package 2 — myapp (build + package dans le cache)
cd ../myapp/
conan create . -s build_type=Release

# Consommation depuis le cache (n'importe où)
mkdir /tmp/run && cd /tmp/run
conan install --requires myapp/1.0 -s build_type=Release -g VirtualRunEnv
source conanrun.sh
myapp
```

### Windows (MSVC 2019)

```bat
:: Package 1 — mymath
cd mymath-prebuilt\
build_library.bat
conan export-pkg . --name mymath --version 1.0 -s os=Windows -s arch=x86_64

:: Package 2 — myapp
cd ..\myapp\
conan create . -s build_type=Release

:: Consommation depuis le cache
mkdir C:\tmp\run && cd C:\tmp\run
conan install --requires myapp/1.0 -s build_type=Release -g VirtualRunEnv
call conanrun.bat
myapp.exe
```

---

## Points importants

### `conan export-pkg` vs `conan create`

| Commande | `build()` appelé ? | Usage |
|----------|--------------------|-------|
| `conan export-pkg` | Non | Binaires pré-compilés hors Conan (`mymath`) |
| `conan create` | Oui | Sources gérées par Conan (`myapp`) |

### Pourquoi `package()` et `package_info()` sont indispensables dans `myapp`

Sans `package()` : l'exécutable reste dans le dossier de build temporaire de
Conan et disparaît. Il ne peut pas être consommé.

Sans `package_info()` (avec `bindirs`) : `VirtualRunEnv` ne sait pas où
chercher l'exécutable et ne l'ajoute pas au `PATH`.

### Pourquoi `exports_sources` est obligatoire dans `myapp`

```python
exports_sources = "CMakeLists.txt", "src/*"
```

Lors du `conan create`, Conan copie les sources dans son propre dossier de
build (dans `~/.conan2/`). Sans cette déclaration, `CMakeLists.txt` n'est
pas copié et CMake échoue.

### `VirtualRunEnv` — comment ça fonctionne

`VirtualRunEnv` génère `conanrun.sh` (Linux) / `conanrun.bat` (Windows).
Ce script injecte dans `PATH` le dossier `bin/` de chaque package déclarant
`cpp_info.bindirs`. Après `source conanrun.sh`, la commande `myapp` pointe
directement vers l'exécutable dans le cache Conan — aucun chemin absolu requis.

### Gestion multi-configurations (Debug / Release)

Pour livrer Debug et Release de `mymath`, compilez les deux variantes et
appelez `export-pkg` deux fois. Pour `myapp`, un seul `conan create` par
`build_type` suffit :

```bash
conan create myapp/ -s build_type=Release
conan create myapp/ -s build_type=Debug
```
