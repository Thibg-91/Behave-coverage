# Packager paho-mqtt-c avec Conan 1.66 (hors-ligne)

Ce tutoriel crée une recette Conan maison pour **paho-mqtt-c**, la bibliothèque C cliente MQTT d'Eclipse Paho, puis la compile en local. Il fonctionne sur une machine **sans accès Internet** : les sources sont fournies sous forme d'archive posée à côté de la recette, ou téléchargées depuis un dépôt interne (Artifactory).

> **⚠️ À propos de la version « 1.13.6 »**
> Il n'existe pas de version 1.13.6 de paho.mqtt.c : les versions publiées sont `1.3.0` → `1.3.16`.
> Tu voulais probablement **1.3.6** (utilisée dans les exemples ci-dessous) ou **1.3.16** (la dernière). La recette marche pour les deux : remplace simplement le numéro de version partout.

---

## Sommaire

1. [Prérequis](#1-prérequis)
2. [Récupérer l'archive des sources](#2-récupérer-larchive-des-sources)
3. [Arborescence du projet](#3-arborescence-du-projet)
4. [La recette `conanfile.py`](#4-la-recette-conanfilepy)
5. [Le fichier `conandata.yml`](#5-le-fichier-conandatayml)
6. [Le `test_package`](#6-le-test_package)
7. [Les profils (GCC / MSVC 2019)](#7-les-profils)
8. [Compiler le package : `conan create`](#8-compiler-le-package--conan-create)
9. [Le flux local pas à pas (pour débugger)](#9-le-flux-local-pas-à-pas-pour-débugger)
10. [Utiliser le package dans un projet](#10-utiliser-le-package-dans-un-projet)
11. [Publier sur Artifactory](#11-publier-sur-artifactory)
12. [Dépannage](#12-dépannage)
13. [Vers Conan 2](#13-vers-conan-2)

---

## 1. Prérequis

| Outil | Version | Vérification |
|---|---|---|
| Conan | 1.66.0 | `conan --version` |
| CMake | ≥ 3.15 | `cmake --version` |
| Compilateur | GCC ≥ 7 ou MSVC 2019 | `gcc --version` / `cl` |
| Python | celui de Conan | – |

Le générateur de build (Make, Ninja ou Visual Studio) doit aussi être installé.

**Réflexe à avoir avant de commencer** : ton Artifactory propose peut-être déjà une recette. Vérifie :

```bash
conan remote list
conan search "paho-mqtt-c*" -r <ton-remote>
```

Si tu n'utilises pas `conancenter` (pas d'accès), désactive-le pour éviter les timeouts :

```bash
conan remote disable conancenter
```

---

## 2. Récupérer l'archive des sources

La recette attend un fichier nommé **exactement** `paho.mqtt.c-<version>.tar.gz`, dont le contenu est rangé dans un dossier racine (par exemple `paho.mqtt.c-1.3.6/`). C'est le format de l'archive de tag GitHub.

**Option A : depuis une machine connectée**, puis copie sur la machine isolée :

```
https://github.com/eclipse-paho/paho.mqtt.c/archive/refs/tags/v1.3.6.tar.gz
```

Renomme le fichier téléchargé `v1.3.6.tar.gz` en `paho.mqtt.c-1.3.6.tar.gz`.

**Option B : via un dépôt « generic remote » Artifactory** qui sert de proxy à github.com (si ton admin en a un). L'URL ressemble à :

```
https://artifactory.mon-entreprise.local/artifactory/<github-remote>/eclipse-paho/paho.mqtt.c/archive/refs/tags/v1.3.6.tar.gz
```

Dans ce cas, tu peux aussi laisser la recette télécharger elle-même l'archive (voir §5).

**Calcule l'empreinte SHA-256** de l'archive. La recette s'en servira pour vérifier le fichier :

```bash
# Linux
sha256sum paho.mqtt.c-1.3.6.tar.gz
```

```powershell
# Windows (PowerShell)
Get-FileHash -Algorithm SHA256 .\paho.mqtt.c-1.3.6.tar.gz
```

Note la valeur : elle va dans `conandata.yml`.

---

## 3. Arborescence du projet

```
paho-mqtt-c/
├── conanfile.py                  # la recette
├── conandata.yml                 # versions + sha256 (+ url optionnelle)
├── paho.mqtt.c-1.3.6.tar.gz      # l'archive des sources (mode hors-ligne)
└── test_package/
    ├── conanfile.py
    ├── CMakeLists.txt
    └── test_package.c
```

---

## 4. La recette `conanfile.py`

La recette utilise les outils « modernes » (`conan.tools.*` : `CMakeToolchain`, `CMakeDeps`, `cmake_layout`). Ils sont disponibles dans Conan 1.66 et facilitent le passage à Conan 2.

```python
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import check_sha256, copy, get, rm, rmdir, unzip

required_conan_version = ">=1.60.0"


class PahoMqttCConan(ConanFile):
    name = "paho-mqtt-c"
    description = "Eclipse Paho C client library for MQTT"
    license = "EPL-2.0"
    url = "https://github.com/eclipse-paho/paho.mqtt.c"
    homepage = "https://eclipse.dev/paho/"
    topics = ("mqtt", "iot", "paho", "c")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "ssl": [True, False],
        "asynchronous": [True, False],
        "high_performance": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "ssl": False,
        "asynchronous": True,
        "high_performance": False,
    }

    # Archive des sources posee a cote de la recette (mode hors-ligne)
    exports_sources = "paho.mqtt.c-*.tar.gz"

    # ------------------------------------------------------------------ #
    # Configuration
    # ------------------------------------------------------------------ #
    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # Bibliotheque C pure : la lib standard C++ ne change pas le binaire
        self.settings.rm_safe("compiler.libcxx")
        self.settings.rm_safe("compiler.cppstd")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        if self.options.ssl:
            # Adapter la version a ce qui est disponible sur votre Artifactory
            self.requires("openssl/1.1.1w")

    def validate(self):
        if self.settings.os not in ("Linux", "Windows", "Macos", "FreeBSD"):
            raise ConanInvalidConfiguration(f"{self.ref} : OS non supporte")

    # ------------------------------------------------------------------ #
    # Sources : archive locale si presente, sinon telechargement
    # ------------------------------------------------------------------ #
    def source(self):
        archive_name = f"paho.mqtt.c-{self.version}.tar.gz"
        data = (self.conan_data or {}).get("sources", {}).get(self.version) or {}
        expected_sha = data.get("sha256")
        # exports_sources sont copies a la racine du dossier source (export_sources_folder),
        # alors que cmake_layout(src_folder="src") place self.source_folder dans "src/"
        local_archive = os.path.join(self.export_sources_folder, archive_name)

        if os.path.isfile(local_archive):
            self.output.info(f"Archive locale utilisee : {archive_name}")
            if expected_sha:
                check_sha256(self, local_archive, expected_sha)
            unzip(self, local_archive, destination=self.source_folder, strip_root=True)
        elif data.get("url"):
            self.output.info(f"Telechargement depuis {data['url']}")
            get(self, **data, strip_root=True)
        else:
            raise ConanInvalidConfiguration(
                f"Ni archive locale '{archive_name}' a cote de la recette, "
                f"ni 'url' dans conandata.yml pour la version {self.version}"
            )

    # ------------------------------------------------------------------ #
    # Build
    # ------------------------------------------------------------------ #
    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["PAHO_BUILD_SHARED"] = bool(self.options.shared)
        tc.variables["PAHO_BUILD_STATIC"] = not self.options.shared
        tc.variables["PAHO_WITH_SSL"] = bool(self.options.ssl)
        tc.variables["PAHO_HIGH_PERFORMANCE"] = bool(self.options.high_performance)
        tc.variables["PAHO_ENABLE_TESTING"] = False
        tc.variables["PAHO_ENABLE_CPACK"] = False
        tc.variables["PAHO_BUILD_DOCUMENTATION"] = False
        tc.variables["PAHO_BUILD_SAMPLES"] = False
        tc.variables["PAHO_BUILD_DEB_PACKAGE"] = False
        # Les vieilles versions declarent cmake_minimum_required(2.8.12),
        # refuse par CMake >= 4.0 sans cette variable (ignoree avant 3.31)
        tc.variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    # ------------------------------------------------------------------ #
    # Package
    # ------------------------------------------------------------------ #
    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "edl-v10", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        copy(self, "epl-v20", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

        cmake = CMake(self)
        cmake.install()

        # On laisse Conan generer les fichiers CMake (CMakeDeps)
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    @property
    def _flavour(self):
        # paho-mqtt3a  : API asynchrone (MQTTAsync.h)
        # paho-mqtt3c  : API synchrone  (MQTTClient.h)
        # suffixe "s"  : variante SSL/TLS
        # ATTENTION : 3a et 3c ne peuvent PAS etre lies ensemble dans un meme
        # binaire en statique (symboles dupliques) -> on n'en expose qu'une.
        base = "paho-mqtt3a" if self.options.asynchronous else "paho-mqtt3c"
        return base + ("s" if self.options.ssl else "")

    def package_info(self):
        flavour = self._flavour
        # Sous Windows, la version statique garde le suffixe "-static"
        lib_name = flavour
        if self.settings.os == "Windows" and not self.options.shared:
            lib_name += "-static"
        # Memes noms de cibles que le eclipse-paho-mqtt-cConfig.cmake officiel
        target = f"eclipse-paho-mqtt-c::{flavour}" + ("" if self.options.shared else "-static")

        self.cpp_info.set_property("cmake_file_name", "eclipse-paho-mqtt-c")
        self.cpp_info.set_property("cmake_target_name", "eclipse-paho-mqtt-c::eclipse-paho-mqtt-c")

        comp = self.cpp_info.components[flavour]
        comp.set_property("cmake_target_name", target)
        comp.libs = [lib_name]

        if self.settings.os == "Windows":
            comp.system_libs = ["ws2_32", "crypt32", "rpcrt4"]
            if self.options.shared:
                comp.defines = ["PAHO_MQTT_IMPORTS=1"]
        elif self.settings.os == "Linux":
            comp.system_libs = ["pthread", "dl", "rt", "anl"]
        elif self.settings.os == "FreeBSD":
            comp.system_libs = ["pthread", "compat"]

        if self.options.ssl:
            comp.requires = ["openssl::ssl", "openssl::crypto"]

        # Noms pour les generateurs legacy de Conan 1 (cmake_find_package[_multi])
        self.cpp_info.names["cmake_find_package"] = "eclipse-paho-mqtt-c"
        self.cpp_info.names["cmake_find_package_multi"] = "eclipse-paho-mqtt-c"
        self.cpp_info.filenames["cmake_find_package"] = "eclipse-paho-mqtt-c"
        self.cpp_info.filenames["cmake_find_package_multi"] = "eclipse-paho-mqtt-c"
        comp.names["cmake_find_package"] = target.split("::")[1]
        comp.names["cmake_find_package_multi"] = target.split("::")[1]
```

### Les points importants de la recette

**Les options**

| Option | Défaut | Effet |
|---|---|---|
| `shared` | `False` | Bibliothèque dynamique (`.so`/`.dll`) ou statique (`.a`/`.lib`) |
| `fPIC` | `True` | Code relogeable en statique (n'existe pas sous Windows) |
| `asynchronous` | `True` | Expose `paho-mqtt3a` (`MQTTAsync.h`) si `True`, `paho-mqtt3c` (`MQTTClient.h`) si `False` |
| `ssl` | `False` | Variantes TLS `3as`/`3cs`. Nécessite `openssl` sur ton remote |
| `high_performance` | `False` | Désactive le traçage interne et le suivi du tas |

**Pourquoi une option `asynchronous` ?** Le CMake de Paho compile toujours les deux bibliothèques, `paho-mqtt3a` et `paho-mqtt3c`. Mais elles embarquent les mêmes symboles internes. En statique, les lier ensemble provoque des erreurs `multiple definition of 'Protocol_processPublication'`. La recette n'expose donc qu'une seule des deux au consommateur. Les deux fichiers restent quand même dans le package.

**Les noms de bibliothèques varient selon la plateforme** (c'est le CMake de Paho qui les choisit) :

| | Statique | Dynamique |
|---|---|---|
| Linux | `libpaho-mqtt3a.a` | `libpaho-mqtt3a.so` |
| Windows | `paho-mqtt3a-static.lib` | `paho-mqtt3a.lib` + `paho-mqtt3a.dll` |

**`PAHO_MQTT_IMPORTS=1`** : sous Windows en `shared`, ce define fait passer les en-têtes en `__declspec(dllimport)`. La recette le propage automatiquement aux consommateurs.

**Les bibliothèques système** :
- Windows : `ws2_32`, `crypt32`, `rpcrt4`.
- Linux : `pthread`, `dl`, `rt`, `anl`. `anl` est indispensable en statique sur les glibc anciennes, par exemple Rocky 8.

**`export_sources_folder`** : avec `cmake_layout(src_folder="src")`, `self.source_folder` pointe sur `src/`. L'archive exportée, elle, reste à la racine. Il faut donc aller la chercher dans `export_sources_folder`.

---

## 5. Le fichier `conandata.yml`

```yaml
sources:
  "1.3.6":
    # url optionnelle : utilisee seulement si l'archive n'est pas posee a cote de la recette
    # url: "https://artifactory.mon-entreprise.local/artifactory/<github-remote>/eclipse-paho/paho.mqtt.c/archive/refs/tags/v1.3.6.tar.gz"
    # sha256 optionnel : decommenter avec l'empreinte de VOTRE archive (sha256sum / Get-FileHash)
    # sha256: "<sha256 de paho.mqtt.c-1.3.6.tar.gz>"
  "1.3.16":
    # sha256: "<sha256 de paho.mqtt.c-1.3.16.tar.gz>"
```

- `sha256` est **optionnel** : décommente la ligne et colle l'empreinte calculée au §2. Si tu le mets, il doit correspondre exactement à **ton** archive. Une archive régénérée autrement, par exemple avec `git archive`, n'a pas la même empreinte que celle de GitHub.
- `url` n'est utile que si l'archive n'est **pas** posée à côté de la recette. La recette la télécharge alors avec `get()`, et l'URL doit être accessible (Artifactory).
- Pour supporter une nouvelle version, il suffit d'ajouter une entrée ici et l'archive correspondante.

---

## 6. Le `test_package`

Le `test_package` est compilé et exécuté automatiquement à la fin de `conan create`. Il prouve que le package s'utilise correctement : en-têtes trouvés, édition de liens réussie, exécution OK. Il n'a pas besoin de broker MQTT.

### `test_package/conanfile.py`

```python
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        opts = self.dependencies["paho-mqtt-c"].options
        if opts.asynchronous:
            # add_compile_definitions() dans le toolchain (pas de cache CMake)
            tc.preprocessor_definitions["PAHO_TEST_ASYNC"] = 1
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_package")
            self.run(bin_path, env="conanrun")
```

> Le define passe par `preprocessor_definitions` et non par `tc.variables`. Dans Conan 1.66, les `variables` sont écrites dans le cache CMake sans `FORCE`. Si le dossier `test_package/build` existe déjà, l'ancienne valeur reste en place quand tu changes l'option.

### `test_package/CMakeLists.txt`

```cmake
cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES C)

find_package(eclipse-paho-mqtt-c REQUIRED CONFIG)

add_executable(test_package test_package.c)
# Cible globale : pointe vers la variante choisie (3a, 3c, 3as ou 3cs)
target_link_libraries(test_package PRIVATE eclipse-paho-mqtt-c::eclipse-paho-mqtt-c)
```

### `test_package/test_package.c`

```c
#include <stdio.h>
#include <stdlib.h>

#ifdef PAHO_TEST_ASYNC
#  include "MQTTAsync.h"
#  define get_version_info MQTTAsync_getVersionInfo
typedef MQTTAsync_nameValue name_value;
#else
#  include "MQTTClient.h"
#  define get_version_info MQTTClient_getVersionInfo
typedef MQTTClient_nameValue name_value;
#endif

int main(void)
{
    int rc;
    name_value* info = get_version_info();

    for (; info && info->name; ++info)
        printf("%s: %s\n", info->name, info->value);

    /* Aucune connexion reseau : on verifie juste que l'API se lie et s'execute */
#ifdef PAHO_TEST_ASYNC
    MQTTAsync client;
    rc = MQTTAsync_create(&client, "tcp://localhost:1883", "conan-test",
                          MQTTCLIENT_PERSISTENCE_NONE, NULL);
    if (rc != MQTTASYNC_SUCCESS) {
        printf("MQTTAsync_create a echoue : %d\n", rc);
        return EXIT_FAILURE;
    }
    MQTTAsync_destroy(&client);
#else
    MQTTClient client;
    rc = MQTTClient_create(&client, "tcp://localhost:1883", "conan-test",
                           MQTTCLIENT_PERSISTENCE_NONE, NULL);
    if (rc != MQTTCLIENT_SUCCESS) {
        printf("MQTTClient_create a echoue : %d\n", rc);
        return EXIT_FAILURE;
    }
    MQTTClient_destroy(&client);
#endif

    printf("paho-mqtt-c OK\n");
    return EXIT_SUCCESS;
}
```

---

## 7. Les profils

Si tu n'as pas encore de profil par défaut :

```bash
conan profile new default --detect
```

### Linux / GCC

Fichier `~/.conan/profiles/linux-gcc` :

```ini
[settings]
os=Linux
arch=x86_64
build_type=Release
compiler=gcc
compiler.version=11
compiler.libcxx=libstdc++11
```

> Sous Linux, `--detect` peut choisir `libstdc++` (ancien ABI). Force le nouvel ABI avec `conan profile update settings.compiler.libcxx=libstdc++11 default`. Ce réglage n'a aucun effet sur paho-mqtt-c, qui est du C pur, mais il compte pour tes autres paquets.

### Windows / MSVC 2019

Fichier `%USERPROFILE%\.conan\profiles\msvc2019` :

```ini
[settings]
os=Windows
arch=x86_64
build_type=Release
compiler=Visual Studio
compiler.version=16
compiler.runtime=MD

[conf]
tools.cmake.cmaketoolchain:generator=Visual Studio 16 2019
```

Pour un build Debug, utilise `-s build_type=Debug -s compiler.runtime=MDd`.

> Lance les commandes depuis une « Developer Command Prompt for VS 2019 » ou un terminal classique. Avec le générateur Visual Studio, CMake trouve MSVC tout seul.

---

## 8. Compiler le package : `conan create`

Depuis le dossier `paho-mqtt-c/`. Le `@` final signifie « sans user/channel » :

```bash
conan create . paho-mqtt-c/1.3.6@ -pr linux-gcc
```

```bat
conan create . paho-mqtt-c/1.3.6@ -pr msvc2019
```

Si votre convention utilise un user/channel :

```bash
conan create . paho-mqtt-c/1.3.6@monorg/stable -pr msvc2019
```

**Résultat attendu** à la fin, produit par le `test_package` :

```
Product name: Eclipse Paho Asynchronous MQTT C Client Library
Version: 1.3.6
...
paho-mqtt-c OK
```

### Variantes courantes

```bash
# Dynamique
conan create . paho-mqtt-c/1.3.6@ -pr msvc2019 -o paho-mqtt-c:shared=True

# API synchrone (MQTTClient.h) au lieu d'asynchrone
conan create . paho-mqtt-c/1.3.6@ -pr msvc2019 -o paho-mqtt-c:asynchronous=False

# Debug
conan create . paho-mqtt-c/1.3.6@ -pr msvc2019 -s build_type=Debug -s compiler.runtime=MDd

# Avec TLS (openssl doit etre disponible sur ton remote)
conan create . paho-mqtt-c/1.3.6@ -pr msvc2019 -o paho-mqtt-c:ssl=True
```

> Pour `ssl=True`, vérifie d'abord que la version d'OpenSSL demandée dans `requirements()` existe : `conan search "openssl*" -r <ton-remote>`. Sinon, adapte la ligne `self.requires("openssl/...")`.

### Vérifier ce qui a été produit

```bash
conan search paho-mqtt-c/1.3.6@           # liste des binaires (un par combinaison settings/options)
conan get paho-mqtt-c/1.3.6@:<package_id> # contenu du conaninfo.txt d'un binaire
```

Le package contient `include/` (7 en-têtes `MQTT*.h`), `lib/`, `bin/` (DLL et `MQTTVersion` en shared) et `licenses/`.

---

## 9. Le flux local pas à pas (pour débugger)

`conan create` refait tout à chaque fois dans le cache. Pour mettre au point la recette, le flux local est plus rapide : chaque étape travaille dans le dossier courant, et tu peux relancer uniquement celle qui pose problème.

```bash
cd paho-mqtt-c

# 1. Resout les dependances et genere toolchain + CMakeDeps (dans build/...)
conan install . paho-mqtt-c/1.3.6@ -pr msvc2019

# 2. Extrait l'archive dans ./src
conan source .

# 3. Compile (relancable autant de fois que necessaire)
conan build .

# 4. Cree le package dans le cache a partir de ce build local
conan export-pkg . paho-mqtt-c/1.3.6@ -pr msvc2019 -f

# 5. Lance le test_package sur le package du cache
conan test test_package paho-mqtt-c/1.3.6@ -pr msvc2019
```

Les dossiers `src/` et `build/` sont créés à côté de la recette. Supprime-les avant un `conan create` pour repartir de zéro. Ce n'est pas obligatoire, mais c'est plus propre.

---

## 10. Utiliser le package dans un projet

### `conanfile.txt` du projet consommateur

```ini
[requires]
paho-mqtt-c/1.3.6

[generators]
CMakeDeps
CMakeToolchain

[options]
paho-mqtt-c:shared=False
paho-mqtt-c:asynchronous=True
```

### `CMakeLists.txt`

```cmake
cmake_minimum_required(VERSION 3.15)
project(mon_app LANGUAGES C)

find_package(eclipse-paho-mqtt-c REQUIRED CONFIG)

add_executable(mon_app main.c)

# Au choix :
#  - cible globale (la variante choisie par les options)
target_link_libraries(mon_app PRIVATE eclipse-paho-mqtt-c::eclipse-paho-mqtt-c)
#  - ou cible explicite, meme nom que le CMake officiel de Paho :
#    eclipse-paho-mqtt-c::paho-mqtt3a-static   (statique)
#    eclipse-paho-mqtt-c::paho-mqtt3a          (shared)
#    ... idem 3c / 3as / 3cs
```

### Build

```bash
conan install . -if build -pr msvc2019
cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE=build/conan_toolchain.cmake
cmake --build build --config Release
```

Sous Linux, ajoute `-DCMAKE_BUILD_TYPE=Release` au `cmake -S`.

> Les noms de cibles sont identiques à ceux du `eclipse-paho-mqtt-cConfig.cmake` officiel. Un projet qui faisait déjà `find_package(eclipse-paho-mqtt-c)` n'a donc rien à changer.

---

## 11. Publier sur Artifactory

```bash
# Authentification (une fois)
conan user -r <ton-remote> -p <token-ou-mot-de-passe> <login>

# Upload de la recette + de tous les binaires construits
conan upload "paho-mqtt-c/1.3.6@" -r <ton-remote> --all --confirm
```

Si ton dépôt Artifactory exige les révisions :

```bash
conan config set general.revisions_enabled=1
```

Active-le **avant** le `conan create`.

---

## 12. Dépannage

| Symptôme | Cause | Solution |
|---|---|---|
| `Ni archive locale 'paho.mqtt.c-X.tar.gz' ... ni 'url'` | Archive absente, mal nommée, ou version non déclarée | Vérifie le nom exact du fichier à côté de `conanfile.py` et l'entrée dans `conandata.yml` |
| `ConanException: sha256 signature failed` | L'empreinte ne correspond pas à ton archive | Recalcule-la (§2) ou supprime la ligne `sha256` |
| `Compatibility with CMake < 3.5 has been removed` | CMake ≥ 4 avec une vieille version de Paho | Déjà géré par `CMAKE_POLICY_VERSION_MINIMUM`. Vérifie que la ligne est bien dans `generate()` |
| `multiple definition of 'Protocol_processPublication'` | Lien simultané de `paho-mqtt3a` **et** `paho-mqtt3c` en statique | N'utiliser qu'une seule variante (option `asynchronous`) |
| `undefined reference to 'getaddrinfo_a'` (Linux, statique) | `libanl` manquante | Déjà dans `system_libs`. Si ton projet ne passe pas par Conan pour le lien, ajoute `anl` |
| `LNK2019 ... __imp_MQTTAsync_create` (Windows) | `PAHO_MQTT_IMPORTS` défini alors que la lib est statique, ou l'inverse | Vérifie que l'option `shared` du consommateur est la même que celle du binaire |
| `LNK1104: cannot open 'paho-mqtt3a.lib'` (Windows statique) | Nom attendu sans `-static` | Déjà géré par la recette (`paho-mqtt3a-static.lib`). Vérifie que tu passes bien par CMakeDeps |
| `openssl/1.1.1w was not found` | OpenSSL indisponible sur le remote | `conan search "openssl*" -r <remote>` puis adapte `requirements()` |
| Timeout vers `center.conan.io` | Remote public inaccessible | `conan remote disable conancenter` |
| Le `test_package` utilise une vieille option | Cache CMake dans `test_package/build` | Supprime `test_package/build/` |

**Voir la sortie complète d'un build en échec** : le dossier de build du cache est indiqué dans les logs, sous la forme `~/.conan/data/paho-mqtt-c/1.3.6/_/_/build/<package_id>/`. Tu peux y relancer `cmake --build .` à la main.

**Nettoyer le cache pour ce paquet** :

```bash
conan remove "paho-mqtt-c/1.3.6@" -f
```

---

## 13. Vers Conan 2

La recette est déjà écrite avec les API communes à Conan 1 et Conan 2. Pour la passer en Conan 2 :

1. Supprime les 6 lignes `cpp_info.names[...]` et `cpp_info.filenames[...]` en fin de `package_info()`. Elles ne servent qu'aux générateurs legacy de Conan 1.
2. Change la commande : `conan create . --version 1.3.6 -pr msvc2019`.
3. Les options s'écrivent `-o "paho-mqtt-c/*:shared=True"`.
4. Profil MSVC : `compiler=msvc`, `compiler.version=192`, `compiler.runtime=dynamic`.

---

*Recette testée avec Conan 1.66.0, CMake 3.28 et GCC 13 (Linux) pour les versions 1.3.6 et 1.3.16. Combinaisons testées : statique et shared, async et sync, Release et Debug, avec et sans SSL. La partie Windows/MSVC suit le CMake de Paho (noms `-static`, libs système, `PAHO_MQTT_IMPORTS`), mais n'a pas pu être exécutée dans l'environnement de test.*
