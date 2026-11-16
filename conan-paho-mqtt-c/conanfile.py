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
