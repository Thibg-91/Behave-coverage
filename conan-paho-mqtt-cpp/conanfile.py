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
