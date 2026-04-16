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

## Linux / macOS — GCC ou Clang

### Étape 1 — Compiler la bibliothèque manuellement

```bash
cd mymath-prebuilt/
chmod +x build_library.sh
./build_library.sh
```

Ce script fait simplement :

```bash
mkdir -p lib
g++ -std=c++17 -O2 -I include/ -c src/mymath.cpp -o mymath.o
ar rcs lib/libmymath.a mymath.o
```

Vous devriez obtenir `lib/libmymath.a`.

### Étape 2 — Empaqueter dans le cache Conan

```bash
conan export-pkg . \
    --name mymath \
    --version 1.0 \
    -s os=Linux \
    -s arch=x86_64
```

> Sur macOS remplacez `-s os=Linux` par `-s os=Macos`.

### Étape 3 — Construire et lancer `myapp`

```bash
cd ../myapp/

conan install . --output-folder=build --build=missing -s build_type=Release

cmake -S . -B build/build/Release \
    -DCMAKE_TOOLCHAIN_FILE=build/build/Release/generators/conan_toolchain.cmake \
    -DCMAKE_BUILD_TYPE=Release

cmake --build build/build/Release

./build/build/Release/myapp
```

Sortie attendue :

```
7 + 5 = 12
```

---

## Windows — MSVC 2019

### Prérequis Windows

- Visual Studio 2019 (Community, Professional ou Enterprise)
- Composant **"Développement Desktop en C++"** installé
- `vswhere.exe` présent (installé automatiquement avec Visual Studio)

### Étape 1 — Créer un profil Conan pour MSVC 2019

Depuis un terminal (PowerShell ou cmd) :

```bat
conan profile detect
```

Conan détecte automatiquement MSVC sur Windows. Vérifiez le profil généré :

```bat
conan profile show
```

Il doit ressembler à :

```ini
[settings]
os=Windows
arch=x86_64
compiler=msvc
compiler.version=193
compiler.runtime=dynamic
compiler.cppstd=14
build_type=Release
```

> **`compiler.version`** : `192` = VS 2019 (MSVC 14.2x), `193` = VS 2022.  
> Conan 2 détecte la version installée — vérifiez que c'est bien `192` si vous
> avez uniquement VS 2019.

### Étape 2 — Compiler la bibliothèque avec MSVC 2019

Depuis PowerShell ou cmd **ordinaire** (le script `build_library.bat` configure
l'environnement MSVC lui-même via `vcvarsall.bat`) :

```bat
cd mymath-prebuilt\
build_library.bat
```

Le script :
1. Localise Visual Studio 2019 avec `vswhere.exe`
2. Appelle `vcvarsall.bat x64` pour préparer l'environnement
3. Compile avec `cl.exe /std:c++17 /O2`
4. Archive avec `lib.exe`

Résultat : `lib\mymath.lib`

### Étape 3 — Empaqueter dans le cache Conan

```bat
conan export-pkg . ^
    --name mymath ^
    --version 1.0 ^
    -s os=Windows ^
    -s arch=x86_64
```

Vérification :

```bat
conan list "mymath/1.0:*"
```

### Étape 4 — Construire `myapp` avec CMake + MSVC

```bat
cd ..\myapp\

:: Installer les dépendances et générer les fichiers CMake
conan install . ^
    --output-folder=build ^
    --build=missing ^
    -s build_type=Release

:: Configurer CMake (générateur multi-config Visual Studio 16)
cmake -S . -B build\build\Release ^
    -G "Visual Studio 16 2019" -A x64 ^
    -DCMAKE_TOOLCHAIN_FILE=build\build\Release\generators\conan_toolchain.cmake

:: Compiler en Release
cmake --build build\build\Release --config Release
```

### Étape 5 — Lancer l'exécutable

```bat
build\build\Release\Release\myapp.exe
```

Sortie :

```
7 + 5 = 12
```

> **Note sur le chemin** : avec le générateur Visual Studio (multi-config),
> CMake place l'exécutable dans un sous-dossier `Release\` ou `Debug\`
> à l'intérieur du répertoire de build.

---

## Récapitulatif des commandes

### Linux

```bash
cd mymath-prebuilt/
./build_library.sh
conan export-pkg . --name mymath --version 1.0 -s os=Linux -s arch=x86_64

cd ../myapp/
conan install . --output-folder=build --build=missing -s build_type=Release
cmake -S . -B build/build/Release \
    -DCMAKE_TOOLCHAIN_FILE=build/build/Release/generators/conan_toolchain.cmake \
    -DCMAKE_BUILD_TYPE=Release
cmake --build build/build/Release
./build/build/Release/myapp
```

### Windows (MSVC 2019)

```bat
cd mymath-prebuilt\
build_library.bat
conan export-pkg . --name mymath --version 1.0 -s os=Windows -s arch=x86_64

cd ..\myapp\
conan install . --output-folder=build --build=missing -s build_type=Release
cmake -S . -B build\build\Release -G "Visual Studio 16 2019" -A x64 -DCMAKE_TOOLCHAIN_FILE=build\build\Release\generators\conan_toolchain.cmake
cmake --build build\build\Release --config Release
build\build\Release\Release\myapp.exe
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
variantes et appelez `export-pkg` deux fois avec des settings différents.

**Linux :**
```bash
# Release
g++ -std=c++17 -O2 -I include/ -c src/mymath.cpp -o mymath.o && ar rcs lib/libmymath.a mymath.o
conan export-pkg . --name mymath --version 1.0 -s os=Linux -s arch=x86_64 -s build_type=Release

# Debug
g++ -std=c++17 -g -O0 -I include/ -c src/mymath.cpp -o mymath.o && ar rcs lib/libmymath.a mymath.o
conan export-pkg . --name mymath --version 1.0 -s os=Linux -s arch=x86_64 -s build_type=Debug
```

**Windows :**
```bat
:: Release
cl.exe /std:c++17 /O2 /EHsc /I include /c src\mymath.cpp /Fo mymath.obj && lib.exe /OUT:lib\mymath.lib mymath.obj
conan export-pkg . --name mymath --version 1.0 -s os=Windows -s arch=x86_64 -s build_type=Release

:: Debug
cl.exe /std:c++17 /Od /Zi /EHsc /I include /c src\mymath.cpp /Fo mymath.obj && lib.exe /OUT:lib\mymath.lib mymath.obj
conan export-pkg . --name mymath --version 1.0 -s os=Windows -s arch=x86_64 -s build_type=Debug
```

> Pour gérer Debug/Release, il faut ajouter `"build_type"` dans les `settings`
> de `conanfile.py` afin que Conan crée un package distinct par configuration.
