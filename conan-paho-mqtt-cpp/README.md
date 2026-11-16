# Packager paho-mqtt-cpp avec Conan 1.66 (hors-ligne)

Ce tutoriel crée une recette Conan maison pour **paho-mqtt-cpp**, le client MQTT C++ d'Eclipse Paho, puis la compile en local. paho-mqtt-cpp est une surcouche C++17 de **paho-mqtt-c**, qu'il faut donc packager d'abord. Tout fonctionne **sans accès Internet** : les sources sont fournies sous forme d'archive posée à côté de la recette, ou téléchargées depuis un dépôt interne (Artifactory).

> Ce dossier suppose que la recette `paho-mqtt-c` du dossier voisin `../conan-paho-mqtt-c/` est disponible. Son `README.md` détaille les étapes communes : récupération des archives, profils, publication.

---

## Sommaire

1. [Quelle version avec quelle version de paho-mqtt-c](#1-quelle-version-avec-quelle-version-de-paho-mqtt-c)
2. [Prérequis](#2-prérequis)
3. [Récupérer les archives des sources](#3-récupérer-les-archives-des-sources)
4. [Arborescence](#4-arborescence)
5. [La recette `conanfile.py`](#5-la-recette-conanfilepy)
6. [Le fichier `conandata.yml`](#6-le-fichier-conandatayml)
7. [Le `test_package`](#7-le-test_package)
8. [Les profils](#8-les-profils)
9. [Compiler : d'abord paho-mqtt-c, puis paho-mqtt-cpp](#9-compiler--dabord-paho-mqtt-c-puis-paho-mqtt-cpp)
10. [Le flux local pas à pas](#10-le-flux-local-pas-à-pas)
11. [Utiliser le package dans un projet](#11-utiliser-le-package-dans-un-projet)
12. [Publier sur Artifactory](#12-publier-sur-artifactory)
13. [Dépannage](#13-dépannage)
14. [Ajouter une autre version](#14-ajouter-une-autre-version)
15. [Vers Conan 2](#15-vers-conan-2)

---

## 1. Quelle version avec quelle version de paho-mqtt-c

Chaque version de paho.mqtt.cpp exige une version minimale de paho.mqtt.c. Ces minimums viennent du README de chaque tag :

| paho.mqtt.cpp | paho.mqtt.c minimale | Standard C++ |
|---|---|---|
| **1.6.0** (ce tutoriel) | **1.3.16** | C++17 |
| 1.5.x | 1.3.14 | C++17 |
| 1.4.x | 1.3.13 | C++11 |
| 1.3.x | 1.3.13 | C++11 |
| 1.2.0 | 1.3.8 | C++11 |
| 1.1 | 1.3.1 | C++11 |

La recette contient cette correspondance dans le dictionnaire `_paho_c_versions`. Elle choisit donc automatiquement `paho-mqtt-c/1.3.16` pour `paho-mqtt-cpp/1.6.0`.

> Les versions ≤ 1.3 de paho.mqtt.cpp ont un CMake différent : elles utilisent un module `FindPahoMqttC`, pas `find_package(eclipse-paho-mqtt-c)`. Cette recette vise la 1.6.0 et devrait convenir aux 1.4/1.5 avec peu de changements (voir §14).

---

## 2. Prérequis

| Outil | Version |
|---|---|
| Conan | 1.66.0 |
| CMake | ≥ 3.15 (paho.mqtt.cpp 1.6.0 exige ≥ 3.13) |
| Compilateur C++17 | GCC ≥ 8, MSVC 2019 (VS 16), Clang ≥ 7 |

Désactive le remote public s'il est inaccessible, sinon `--build=missing` part en timeout :

```bash
conan remote disable conancenter
```

---

## 3. Récupérer les archives des sources

Il faut **deux** archives, nommées exactement comme suit :

| Archive | À poser dans | Source (machine connectée ou proxy Artifactory) |
|---|---|---|
| `paho.mqtt.c-1.3.16.tar.gz` | `conan-paho-mqtt-c/` | `https://github.com/eclipse-paho/paho.mqtt.c/archive/refs/tags/v1.3.16.tar.gz` |
| `paho.mqtt.cpp-1.6.0.tar.gz` | `conan-paho-mqtt-cpp/` | `https://github.com/eclipse-paho/paho.mqtt.cpp/archive/refs/tags/v1.6.0.tar.gz` |

GitHub nomme ces fichiers `v1.3.16.tar.gz` et `v1.6.0.tar.gz` : renomme-les. Le contenu doit être rangé dans un dossier racine (`paho.mqtt.cpp-1.6.0/...`), ce qui est le cas des archives de tag GitHub.

Pour l'empreinte SHA-256, qui est optionnelle :

```bash
sha256sum paho.mqtt.cpp-1.6.0.tar.gz                                  # Linux
```

```powershell
Get-FileHash -Algorithm SHA256 .\paho.mqtt.cpp-1.6.0.tar.gz           # Windows
```

> L'archive GitHub de paho.mqtt.cpp ne contient pas le sous-module `externals/paho.mqtt.c`. Ce n'est pas un problème : la recette utilise le paquet Conan `paho-mqtt-c` (`PAHO_WITH_MQTT_C=OFF`).

---

## 4. Arborescence

```
conan-paho-mqtt-c/                  # recette C (prérequis)
└── ...
conan-paho-mqtt-cpp/
├── conanfile.py
├── conandata.yml
├── paho.mqtt.cpp-1.6.0.tar.gz      # archive des sources (non versionnée)
└── test_package/
    ├── conanfile.py
    ├── CMakeLists.txt
    └── test_package.cpp
```

---

## 5. La recette `conanfile.py`

```python
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import check_sha256, copy, get, load, replace_in_file, rm, rmdir, unzip
from conan.tools.scm import Version

required_conan_version = ">=1.60.0"


class PahoMqttCppConan(ConanFile):
    name = "paho-mqtt-cpp"
    description = "Eclipse Paho C++ client library for MQTT (wrapper de paho-mqtt-c)"
    license = "EPL-2.0"
    url = "https://github.com/eclipse-paho/paho.mqtt.cpp"
    homepage = "https://eclipse.dev/paho/"
    topics = ("mqtt", "iot", "paho", "c++")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "ssl": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "ssl": False,
    }

    # Archive des sources posee a cote de la recette (mode hors-ligne)
    exports_sources = "paho.mqtt.cpp-*.tar.gz"

    # Version de paho-mqtt-c exigee par chaque version de paho-mqtt-cpp
    # (voir le README de chaque tag paho.mqtt.cpp)
    _paho_c_versions = {
        "1.6.0": "1.3.16",
    }

    @property
    def _min_cppstd(self):
        return 17

    @property
    def _compilers_minimum_version(self):
        # Versions minimales pour un C++17 complet
        return {
            "gcc": "8",
            "clang": "7",
            "apple-clang": "12",
            "Visual Studio": "15",  # Conan 1 : VS 2017
            "msvc": "191",          # Conan 2 / Conan 1 "msvc"
        }

    # ------------------------------------------------------------------ #
    # Configuration
    # ------------------------------------------------------------------ #
    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")
        # Le wrapper C++ est construit sur l'API asynchrone C (paho-mqtt3a / 3as)
        self.options["paho-mqtt-c"].asynchronous = True
        self.options["paho-mqtt-c"].ssl = self.options.ssl

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        c_version = self._paho_c_versions.get(str(self.version))
        if c_version is None:
            raise ConanInvalidConfiguration(
                f"Version {self.version} inconnue : ajoute-la dans _paho_c_versions"
            )
        # transitive_headers : les en-tetes C++ incluent MQTTAsync.h.
        # Ignore par Conan 1 (les en-tetes sont toujours propages), requis en Conan 2.
        self.requires(f"paho-mqtt-c/{c_version}", transitive_headers=True)

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, self._min_cppstd)
        minimum = self._compilers_minimum_version.get(str(self.settings.compiler))
        if minimum and Version(self.settings.compiler.version) < minimum:
            raise ConanInvalidConfiguration(
                f"{self.ref} exige C++{self._min_cppstd} : "
                f"{self.settings.compiler} >= {minimum} necessaire"
            )

        c_opts = self.dependencies["paho-mqtt-c"].options
        if not c_opts.asynchronous:
            raise ConanInvalidConfiguration(
                f"{self.ref} exige paho-mqtt-c:asynchronous=True"
            )
        if bool(c_opts.ssl) != bool(self.options.ssl):
            raise ConanInvalidConfiguration(
                f"{self.ref} : l'option ssl doit etre identique a celle de paho-mqtt-c"
            )

    # ------------------------------------------------------------------ #
    # Sources : archive locale si presente, sinon telechargement
    # ------------------------------------------------------------------ #
    def source(self):
        archive_name = f"paho.mqtt.cpp-{self.version}.tar.gz"
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
        tc.variables["PAHO_WITH_MQTT_C"] = False   # on utilise le paquet Conan paho-mqtt-c
        tc.variables["PAHO_BUILD_SAMPLES"] = False
        tc.variables["PAHO_BUILD_EXAMPLES"] = False
        tc.variables["PAHO_BUILD_TESTS"] = False
        tc.variables["PAHO_BUILD_DOCUMENTATION"] = False
        tc.variables["PAHO_BUILD_DEB_PACKAGE"] = False
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

    def _patch_sources(self):
        # Le CMake amont lie paho-mqttpp3-static a "eclipse-paho-mqtt-c::paho-mqtt3a-static"
        # et paho-mqttpp3-shared a "eclipse-paho-mqtt-c::paho-mqtt3a" : cela impose que
        # paho-mqtt-c soit construit avec le meme type (static/shared).
        # On passe par la cible globale du paquet Conan, valable dans tous les cas.
        cmake_src = os.path.join(self.source_folder, "src", "CMakeLists.txt")
        global_target = "eclipse-paho-mqtt-c::eclipse-paho-mqtt-c"
        content = load(self, cmake_src)
        if "${PAHO_MQTT_C_LIB}" in content:
            replace_in_file(self, cmake_src, "${PAHO_MQTT_C_LIB}-static", global_target)
            replace_in_file(self, cmake_src, "${PAHO_MQTT_C_LIB}", global_target)
        elif global_target not in content:
            # Ni l'original ni le patch : le CMake amont a change, il faut revoir le patch
            raise ConanInvalidConfiguration(f"Patch impossible sur {cmake_src}")
        # sinon : deja patche (2e "conan build ." dans le flux local)

    def build(self):
        self._patch_sources()
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    # ------------------------------------------------------------------ #
    # Package
    # ------------------------------------------------------------------ #
    def package(self):
        for lic in ("LICENSE", "NOTICE", "edl-v10", "epl-v20"):
            copy(self, lic, src=self.source_folder,
                 dst=os.path.join(self.package_folder, "licenses"))

        cmake = CMake(self)
        cmake.install()

        # On laisse Conan generer les fichiers CMake (CMakeDeps)
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "share"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

    def package_info(self):
        suffix = "shared" if self.options.shared else "static"
        # Sous Windows, la version statique garde le suffixe "-static"
        lib_name = "paho-mqttpp3"
        if self.settings.os == "Windows" and not self.options.shared:
            lib_name += "-static"

        # Memes noms que le PahoMqttCppConfig.cmake officiel :
        #   PahoMqttCpp::paho-mqttpp3        (alias, toujours present)
        #   PahoMqttCpp::paho-mqttpp3-static / PahoMqttCpp::paho-mqttpp3-shared
        self.cpp_info.set_property("cmake_file_name", "PahoMqttCpp")
        self.cpp_info.set_property("cmake_target_name", "PahoMqttCpp::paho-mqttpp3")

        comp = self.cpp_info.components["paho-mqttpp3"]
        comp.set_property("cmake_target_name", f"PahoMqttCpp::paho-mqttpp3-{suffix}")
        comp.libs = [lib_name]
        c_flavour = "paho-mqtt3as" if self.options.ssl else "paho-mqtt3a"
        comp.requires = [f"paho-mqtt-c::{c_flavour}"]

        if self.settings.os == "Windows":
            comp.system_libs = ["ws2_32"]
            if self.options.shared:
                comp.defines = ["PAHO_MQTTPP_IMPORTS"]
        elif self.settings.os in ("Linux", "FreeBSD"):
            comp.system_libs = ["pthread", "m"]

        # Noms pour les generateurs legacy de Conan 1 (cmake_find_package[_multi])
        self.cpp_info.names["cmake_find_package"] = "PahoMqttCpp"
        self.cpp_info.names["cmake_find_package_multi"] = "PahoMqttCpp"
        self.cpp_info.filenames["cmake_find_package"] = "PahoMqttCpp"
        self.cpp_info.filenames["cmake_find_package_multi"] = "PahoMqttCpp"
        comp.names["cmake_find_package"] = f"paho-mqttpp3-{suffix}"
        comp.names["cmake_find_package_multi"] = f"paho-mqttpp3-{suffix}"
```

### Les points importants

**Les options**

| Option | Défaut | Effet |
|---|---|---|
| `shared` | `False` | `paho-mqttpp3` en dynamique (`.so`/`.dll`) ou statique |
| `fPIC` | `True` | Code relogeable en statique (n'existe pas sous Windows) |
| `ssl` | `False` | Utilise `paho-mqtt3as` au lieu de `paho-mqtt3a`. Nécessite `openssl` sur ton remote |

**Les options imposées à paho-mqtt-c** dans `configure()` :
- `asynchronous=True` : le wrapper C++ repose sur l'API asynchrone C (`MQTTAsync.h`). Les deux clients C++, `mqtt::client` et `mqtt::async_client`, l'utilisent.
- `ssl` : la même valeur que paho-mqtt-cpp. `validate()` vérifie ensuite que la combinaison est cohérente.

**Le patch du CMake (`_patch_sources`)** : le CMake amont lie `paho-mqttpp3-static` à `eclipse-paho-mqtt-c::paho-mqtt3a-static`, et `paho-mqttpp3-shared` à `eclipse-paho-mqtt-c::paho-mqtt3a`. Sans patch, paho-mqtt-c devrait avoir le même type, statique ou dynamique, que paho-mqtt-cpp. La recette remplace ces cibles par la cible globale `eclipse-paho-mqtt-c::eclipse-paho-mqtt-c` du paquet Conan. Toutes les combinaisons marchent alors, par exemple un paho-mqtt-cpp en DLL avec un paho-mqtt-c statique embarqué. Le patch est idempotent, donc tu peux relancer `conan build .` dans le flux local.

**C++17** : `validate()` refuse un `compiler.cppstd` inférieur à 17 et les compilateurs trop anciens.

**Les noms de bibliothèques** (choisis par le CMake amont) :

| | Statique | Dynamique |
|---|---|---|
| Linux | `libpaho-mqttpp3.a` | `libpaho-mqttpp3.so` |
| Windows | `paho-mqttpp3-static.lib` | `paho-mqttpp3.lib` + `paho-mqttpp3.dll` |

**Windows en DLL** : le CMake amont exporte tous les symboles avec `CMAKE_WINDOWS_EXPORT_ALL_SYMBOLS`. La recette ajoute `PAHO_MQTTPP_IMPORTS` chez les consommateurs pour que `export.h` passe en `__declspec(dllimport)`.

**Les cibles CMake** sont les mêmes que celles du `PahoMqttCppConfig.cmake` officiel :
- `PahoMqttCpp::paho-mqttpp3` : toujours présente, c'est celle à utiliser.
- `PahoMqttCpp::paho-mqttpp3-static` ou `PahoMqttCpp::paho-mqttpp3-shared`, selon l'option `shared`.

---

## 6. Le fichier `conandata.yml`

```yaml
sources:
  "1.6.0":
    # url optionnelle : utilisee seulement si l'archive n'est pas posee a cote de la recette
    # url: "https://artifactory.mon-entreprise.local/artifactory/<github-remote>/eclipse-paho/paho.mqtt.cpp/archive/refs/tags/v1.6.0.tar.gz"
    # sha256 optionnel : decommenter avec l'empreinte de VOTRE archive (sha256sum / Get-FileHash)
    # sha256: "<sha256 de paho.mqtt.cpp-1.6.0.tar.gz>"
```

Les deux champs sont facultatifs. Décommente `sha256` avec l'empreinte de **ton** archive. `url` ne sert que si l'archive n'est pas posée à côté de la recette.

---

## 7. Le `test_package`

Il compile un petit programme qui crée un `mqtt::async_client` et un `mqtt::client`, puis construit des options de connexion et un message. Il n'a besoin d'aucun broker.

### `test_package/conanfile.py`

```python
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_package")
            self.run(bin_path, env="conanrun")
```

### `test_package/CMakeLists.txt`

```cmake
cmake_minimum_required(VERSION 3.15)
project(test_package LANGUAGES CXX)

find_package(PahoMqttCpp REQUIRED CONFIG)

add_executable(test_package test_package.cpp)
target_compile_features(test_package PRIVATE cxx_std_17)
# Meme cible que le PahoMqttCppConfig.cmake officiel
target_link_libraries(test_package PRIVATE PahoMqttCpp::paho-mqttpp3)
```

### `test_package/test_package.cpp`

```cpp
#include <cstdlib>
#include <iostream>

#include "mqtt/async_client.h"
#include "mqtt/client.h"

int main()
{
    std::cout << mqtt::PAHO_MQTTPP_VERSION_STR << std::endl;

    try {
        // Aucune connexion reseau : on verifie que l'API se lie et s'execute
        mqtt::async_client async_cli("tcp://localhost:1883", "conan-test-async");
        mqtt::client sync_cli("tcp://localhost:1883", "conan-test-sync");

        auto conn_opts = mqtt::connect_options_builder()
                             .clean_session()
                             .automatic_reconnect(false)
                             .finalize();

        auto msg = mqtt::make_message("conan/test", "hello", 1, false);

        std::cout << "client id : " << async_cli.get_client_id() << "\n"
                  << "topic     : " << msg->get_topic() << "\n"
                  << "payload   : " << msg->to_string() << "\n"
                  << "connecte  : " << std::boolalpha << async_cli.is_connected()
                  << std::endl;
        (void)conn_opts;
        (void)sync_cli;
    }
    catch (const mqtt::exception& e) {
        std::cerr << "Erreur MQTT : " << e.what() << std::endl;
        return EXIT_FAILURE;
    }

    std::cout << "paho-mqtt-cpp OK" << std::endl;
    return EXIT_SUCCESS;
}
```

---

## 8. Les profils

### Linux / GCC

```ini
[settings]
os=Linux
arch=x86_64
build_type=Release
compiler=gcc
compiler.version=11
compiler.libcxx=libstdc++11
```

> Pour du C++, `compiler.libcxx=libstdc++11` compte vraiment. Utilise le même réglage pour paho-mqtt-cpp et pour ton application, sinon tu auras des erreurs de lien sur `std::string`.

### Windows / MSVC 2019

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

Pour un build Debug, ajoute `-s build_type=Debug -s compiler.runtime=MDd`. Le runtime doit être le même pour paho-mqtt-c, paho-mqtt-cpp et ton application.

---

## 9. Compiler : d'abord paho-mqtt-c, puis paho-mqtt-cpp

### Étape 1 : paho-mqtt-c 1.3.16

```bash
cd conan-paho-mqtt-c
conan create . paho-mqtt-c/1.3.16@ -pr msvc2019
```

### Étape 2 : paho-mqtt-cpp 1.6.0

```bash
cd ../conan-paho-mqtt-cpp
conan create . paho-mqtt-cpp/1.6.0@ -pr msvc2019 --build=missing
```

`--build=missing` construit au passage le binaire de paho-mqtt-c qui manquerait pour la combinaison d'options demandée, par exemple `ssl=True` ou `paho-mqtt-c:shared=True`.

**Résultat attendu** :

```
Paho MQTT C++ (mqttpp) v1.6.0
client id : conan-test-async
topic     : conan/test
payload   : hello
connecte  : false
paho-mqtt-cpp OK
```

### Variantes

```bash
# paho-mqtt-cpp en DLL / .so (paho-mqtt-c reste statique et y est embarque)
conan create . paho-mqtt-cpp/1.6.0@ -pr msvc2019 --build=missing -o paho-mqtt-cpp:shared=True

# Tout en dynamique
conan create . paho-mqtt-cpp/1.6.0@ -pr msvc2019 --build=missing \
    -o paho-mqtt-cpp:shared=True -o paho-mqtt-c:shared=True

# Debug
conan create . paho-mqtt-cpp/1.6.0@ -pr msvc2019 --build=missing \
    -s build_type=Debug -s compiler.runtime=MDd

# TLS (openssl doit etre disponible sur ton remote)
conan create . paho-mqtt-cpp/1.6.0@ -pr msvc2019 --build=missing -o paho-mqtt-cpp:ssl=True
```

> Sous Windows (cmd), remplace les `\` de fin de ligne par `^`, ou écris tout sur une seule ligne.

---

## 10. Le flux local pas à pas

Ce flux sert à mettre au point la recette sans tout refaire dans le cache. paho-mqtt-c doit déjà être dans le cache (étape 1 du §9).

```bash
cd conan-paho-mqtt-cpp
conan install . paho-mqtt-cpp/1.6.0@ -pr msvc2019      # deps + toolchain dans build/...
conan source .                                         # extrait l'archive dans ./src
conan build .                                          # compile (relancable)
conan export-pkg . paho-mqtt-cpp/1.6.0@ -pr msvc2019 -f
conan test test_package paho-mqtt-cpp/1.6.0@ -pr msvc2019
```

Supprime `src/`, `build/` et `test_package/build/` pour repartir de zéro. Ces dossiers sont dans le `.gitignore`.

---

## 11. Utiliser le package dans un projet

### `conanfile.txt`

```ini
[requires]
paho-mqtt-cpp/1.6.0

[generators]
CMakeDeps
CMakeToolchain

[options]
paho-mqtt-cpp:shared=False
```

paho-mqtt-c est tiré automatiquement, en version 1.3.16 avec les bonnes options.

### `CMakeLists.txt`

```cmake
cmake_minimum_required(VERSION 3.15)
project(mon_app LANGUAGES CXX)

find_package(PahoMqttCpp REQUIRED CONFIG)

add_executable(mon_app main.cpp)
target_compile_features(mon_app PRIVATE cxx_std_17)
target_link_libraries(mon_app PRIVATE PahoMqttCpp::paho-mqttpp3)
```

### Build

```bash
conan install . -if build -pr msvc2019
cmake -S . -B build -DCMAKE_TOOLCHAIN_FILE=build/conan_toolchain.cmake
cmake --build build --config Release
```

Sous Linux, ajoute `-DCMAKE_BUILD_TYPE=Release` au `cmake -S`.

> En dynamique sous Windows, les DLL `paho-mqttpp3.dll` (et `paho-mqtt3a.dll` si paho-mqtt-c est aussi en shared) doivent être trouvables à l'exécution. Le script `conanrun.bat` généré par le générateur `VirtualRunEnv` règle le `PATH`. Tu peux aussi copier les DLL à côté de l'exécutable.

---

## 12. Publier sur Artifactory

Publie les **deux** paquets, sinon les autres machines ne pourront pas résoudre la dépendance :

```bash
conan user -r <ton-remote> -p <token> <login>
conan upload "paho-mqtt-c/1.3.16@"  -r <ton-remote> --all --confirm
conan upload "paho-mqtt-cpp/1.6.0@" -r <ton-remote> --all --confirm
```

---

## 13. Dépannage

| Symptôme | Cause | Solution |
|---|---|---|
| `paho-mqtt-c/1.3.16 was not found` | Recette C pas encore créée ni uploadée | Étape 1 du §9, ou `conan upload` depuis la machine qui l'a construite |
| `Missing prebuilt package for 'paho-mqtt-c/1.3.16'` | Pas de binaire C pour cette combinaison d'options | Ajoute `--build=missing` |
| `Max retries exceeded ... center.conan.io` | Le remote public est tenté par `--build=missing` | `conan remote disable conancenter` |
| `Current cppstd (14) is lower than the required C++ standard (17)` | Profil en C++14 | `compiler.cppstd=17` (ou supprime le réglage) |
| `... exige C++17 : gcc >= 8 necessaire` | Compilateur trop ancien | GCC ≥ 8 / MSVC 2019 |
| `Patch impossible sur .../src/CMakeLists.txt` | Le CMake amont a changé (autre version) | Adapter `_patch_sources()` (§14) |
| `Could NOT find eclipse-paho-mqtt-c (... version 1.3.14)` | paho-mqtt-c trop ancien | Respecter le tableau du §1 |
| `undefined reference to std::__cxx11::basic_string...` (Linux) | Mélange `libstdc++` / `libstdc++11` | Même `compiler.libcxx` partout |
| `LNK2038: mismatch detected for 'RuntimeLibrary'` (Windows) | Runtime différent entre paquets et application (MD/MDd/MT) | Même `compiler.runtime` partout |
| `LNK2019 ... __imp_...` (Windows) | Mauvais mélange statique/DLL côté consommateur | Ne pas définir `PAHO_MQTTPP_IMPORTS` à la main, laisser CMakeDeps le faire |
| Le `.dll` est introuvable au lancement | `PATH` | Activer `conanrun.bat` ou copier les DLL |

---

## 14. Ajouter une autre version

1. Ajoute l'archive `paho.mqtt.cpp-<version>.tar.gz` et une entrée dans `conandata.yml`.
2. Ajoute la version dans `_paho_c_versions`, avec la version C indiquée dans son README (tableau du §1). Par exemple `"1.5.3": "1.3.16"` : une version C plus récente que le minimum convient.
3. Pour 1.4.x : la lib est en C++11. Abaisse `_min_cppstd` à 11 pour ces versions, par exemple avec un test sur `Version(self.version)`.
4. Pour ≤ 1.3.x : le CMake est différent (module `FindPahoMqttC`, options `PAHO_BUILD_STATIC`/`PAHO_BUILD_SHARED` sans cibles `eclipse-paho-mqtt-c::`). `_patch_sources()` lèvera une erreur : c'est voulu, il faudra un autre patch.

---

## 15. Vers Conan 2

La recette utilise déjà les API communes à Conan 1 et Conan 2. `transitive_headers=True` est ignoré par Conan 1, mais il est indispensable en Conan 2, car `mqtt/async_client.h` inclut `MQTTAsync.h`.

1. Supprime les lignes `cpp_info.names[...]`, `cpp_info.filenames[...]` et `comp.names[...]` en fin de `package_info()`.
2. Commande : `conan create . --version 1.6.0 -pr msvc2019 --build=missing`.
3. Options : `-o "paho-mqtt-cpp/*:shared=True" -o "paho-mqtt-c/*:shared=True"`.
4. Profil MSVC : `compiler=msvc`, `compiler.version=192`, `compiler.runtime=dynamic`, `compiler.cppstd=17`.

---

*Recette testée avec Conan 1.66.0, CMake 3.28 et GCC 13 (Linux), pour paho-mqtt-cpp 1.6.0 et paho-mqtt-c 1.3.16. Combinaisons testées : cpp statique ou shared × C statique ou shared, Release et Debug, avec et sans SSL, plus le flux local. Le refus d'un `compiler.cppstd=14` a aussi été vérifié. La partie Windows/MSVC suit le CMake amont (noms `-static`, `ws2_32`, `PAHO_MQTTPP_IMPORTS`), mais n'a pas pu être exécutée dans l'environnement de test.*
