import json
import os
import re
import textwrap

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import check_sha256, copy, get, load, rm, rmdir, save, unzip
from conan.tools.microsoft import is_msvc, is_msvc_static_runtime

required_conan_version = ">=1.60.0"


class ProtobufConan(ConanFile):
    name = "protobuf"
    description = "Protocol Buffers - Google's data interchange format"
    license = "BSD-3-Clause"
    url = "https://github.com/protocolbuffers/protobuf"
    homepage = "https://protobuf.dev"
    topics = ("protocol-buffers", "protoc", "serialization", "rpc")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "with_zlib": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "with_zlib": False,
    }

    # Archive des sources posee a cote de la recette (mode hors-ligne)
    exports_sources = "protobuf-*.tar.gz"

    # Version de la recette Conan = version de la lib C++ (5.29.6).
    # Le tag GitHub / l'archive, eux, portent le numero "protoc" (29.6).
    @property
    def _upstream_version(self):
        major, minor, patch = str(self.version).split(".")
        return f"{minor}.{patch}"

    # Version d'abseil a utiliser pour chaque version de protobuf
    # (abseil LTS 20240116 epingle par protobuf 29.x dans protobuf_deps.bzl)
    _abseil_versions = {
        "5.29.6": "20240116.2",
    }

    _deps_file = os.path.join("lib", "conan", "protobuf-abseil-deps.json")
    _cmake_dir = os.path.join("lib", "cmake", "protobuf")

    # ------------------------------------------------------------------ #
    # Configuration
    # ------------------------------------------------------------------ #
    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        absl_version = self._abseil_versions.get(str(self.version))
        if absl_version is None:
            raise ConanInvalidConfiguration(
                f"Version {self.version} inconnue : ajoute-la dans _abseil_versions"
            )
        # transitive_headers : les en-tetes protobuf incluent ceux d'abseil.
        # Ignore par Conan 1 (en-tetes toujours propages), requis en Conan 2.
        self.requires(f"abseil/{absl_version}", transitive_headers=True)
        if self.options.with_zlib:
            # Adapter a la version disponible sur votre Artifactory
            self.requires("zlib/[>=1.2.11 <2]")

    def validate(self):
        if not self.settings.compiler.get_safe("cppstd"):
            raise ConanInvalidConfiguration(
                f"{self.ref} : definis compiler.cppstd dans le profil (ex. 17), "
                "identique pour abseil, protobuf et ton application."
            )
        check_min_cppstd(self, 14)
        if self.options.shared and is_msvc(self):
            # En DLL sous MSVC, protobuf exige la DLL monolithique absl::abseil_dll
            raise ConanInvalidConfiguration(
                f"{self.ref} : shared=True n'est pas gere sous MSVC par cette recette"
            )

    def package_id(self):
        # En statique, abseil est embarque dans libprotobuf / protoc : toute
        # variation d'abseil (options, revision...) doit donner un autre binaire.
        # (Le mode par defaut de Conan 1 ne regarde que la version majeure.)
        self.info.requires["abseil"].full_package_mode()

    # ------------------------------------------------------------------ #
    # Sources : archive locale si presente, sinon telechargement
    # ------------------------------------------------------------------ #
    def source(self):
        archive_name = f"protobuf-{self._upstream_version}.tar.gz"
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
        tc.variables["protobuf_BUILD_SHARED_LIBS"] = bool(self.options.shared)
        tc.variables["protobuf_ABSL_PROVIDER"] = "package"   # abseil vient de Conan
        tc.variables["protobuf_WITH_ZLIB"] = bool(self.options.with_zlib)
        tc.variables["protobuf_BUILD_TESTS"] = False
        tc.variables["protobuf_BUILD_CONFORMANCE"] = False
        tc.variables["protobuf_BUILD_EXAMPLES"] = False
        tc.variables["protobuf_BUILD_LIBUPB"] = False
        tc.variables["protobuf_BUILD_PROTOC_BINARIES"] = True
        tc.variables["protobuf_BUILD_LIBPROTOC"] = True
        tc.variables["protobuf_INSTALL"] = True
        if is_msvc(self):
            # Par defaut protobuf force /MT en statique : on suit le profil Conan
            tc.variables["protobuf_MSVC_STATIC_RUNTIME"] = is_msvc_static_runtime(self)
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
    def _abseil_used_targets(self):
        """Liste protobuf_ABSL_USED_TARGETS lue dans cmake/abseil-cpp.cmake (cas non-DLL)."""
        content = load(self, os.path.join(self.source_folder, "cmake", "abseil-cpp.cmake"))
        # Plusieurs set(protobuf_ABSL_USED_TARGETS ...) existent (cas DLL MSVC = abseil_dll) :
        # on garde la liste la plus longue, celle des cibles absl:: individuelles.
        blocks = re.findall(r"set\(protobuf_ABSL_USED_TARGETS(.*?)\)", content, re.S)
        targets = max((re.findall(r"absl::(\w+)", b) for b in blocks), key=len, default=[])
        if len(targets) < 10:
            raise ConanInvalidConfiguration("protobuf_ABSL_USED_TARGETS introuvable dans abseil-cpp.cmake")
        return targets

    def package(self):
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

        save(self, os.path.join(self.package_folder, self._deps_file),
             json.dumps(self._abseil_used_targets(), indent=2))

        # On garde protobuf-generate.cmake (fonction protobuf_generate) et
        # protobuf-options.cmake ; Conan genere le reste (CMakeDeps).
        # protobuf-module.cmake (mode FindProtobuf) lit IMPORTED_LOCATION sur les
        # cibles, ce qui ne marche pas avec les cibles INTERFACE de CMakeDeps.
        cmake_dir = os.path.join(self.package_folder, self._cmake_dir)
        for f in ("protobuf-config.cmake", "protobuf-config-version.cmake",
                  "protobuf-targets*.cmake", "protobuf-module.cmake"):
            rm(self, f, cmake_dir)
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake", "utf8_range"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))
        rm(self, "*.pdb", self.package_folder, recursive=True)

        # Cible protobuf::protoc (l'executable), utilisee par protobuf_generate()
        save(self, os.path.join(cmake_dir, "protobuf-conan-protoc-target.cmake"), textwrap.dedent("""\
            if(NOT TARGET protobuf::protoc)
                get_filename_component(_protobuf_root "${CMAKE_CURRENT_LIST_DIR}/../../.." ABSOLUTE)
                find_program(PROTOC_PROGRAM NAMES protoc
                             PATHS "${_protobuf_root}/bin" NO_DEFAULT_PATH)
                if(NOT PROTOC_PROGRAM)
                    message(FATAL_ERROR "protoc introuvable dans ${_protobuf_root}/bin")
                endif()
                add_executable(protobuf::protoc IMPORTED)
                set_property(TARGET protobuf::protoc PROPERTY IMPORTED_LOCATION "${PROTOC_PROGRAM}")
                set(Protobuf_PROTOC_EXECUTABLE "${PROTOC_PROGRAM}")
            endif()
        """))

    def package_info(self):
        lib_prefix = "lib" if is_msvc(self) else ""
        lib_suffix = "d" if self.settings.build_type == "Debug" else ""   # protobuf_DEBUG_POSTFIX
        absl_deps = [f"abseil::{name}" for name in
                     json.loads(load(self, os.path.join(self.package_folder, self._deps_file)))]

        self.cpp_info.set_property("cmake_file_name", "protobuf")
        self.cpp_info.set_property("cmake_target_name", "protobuf::protobuf")
        self.cpp_info.set_property("cmake_build_modules", [
            os.path.join(self._cmake_dir, "protobuf-conan-protoc-target.cmake"),
            os.path.join(self._cmake_dir, "protobuf-generate.cmake"),
            os.path.join(self._cmake_dir, "protobuf-options.cmake"),
        ])

        system_libs = []
        if self.settings.os in ("Linux", "FreeBSD"):
            system_libs = ["pthread", "m"]
        defines = ["PROTOBUF_USE_DLLS"] if self.options.shared else []

        # utf8_range (livre avec protobuf, cibles utf8_range::*)
        utf8 = self.cpp_info.components["utf8_range"]
        utf8.set_property("cmake_target_name", "utf8_range::utf8_range")
        utf8.libs = ["utf8_range"]

        utf8v = self.cpp_info.components["utf8_validity"]
        utf8v.set_property("cmake_target_name", "utf8_range::utf8_validity")
        utf8v.libs = ["utf8_validity"]
        utf8v.requires = ["abseil::strings"]

        # libprotobuf-lite
        lite = self.cpp_info.components["libprotobuf-lite"]
        lite.set_property("cmake_target_name", "protobuf::libprotobuf-lite")
        lite.libs = [f"{lib_prefix}protobuf-lite{lib_suffix}"]
        lite.requires = absl_deps + ["utf8_validity"]
        lite.system_libs = system_libs
        lite.defines = defines

        # libprotobuf
        full = self.cpp_info.components["libprotobuf"]
        full.set_property("cmake_target_name", "protobuf::libprotobuf")
        full.libs = [f"{lib_prefix}protobuf{lib_suffix}"]
        full.requires = absl_deps + ["utf8_validity"]
        if self.options.with_zlib:
            full.requires.append("zlib::zlib")
        full.system_libs = system_libs
        full.defines = defines

        # libprotoc (pour ecrire des plugins protoc)
        protoc = self.cpp_info.components["libprotoc"]
        protoc.set_property("cmake_target_name", "protobuf::libprotoc")
        protoc.libs = [f"{lib_prefix}protoc{lib_suffix}"]
        protoc.requires = ["libprotobuf"] + absl_deps
        protoc.defines = defines

        # Generateurs legacy de Conan 1
        self.cpp_info.names["cmake_find_package"] = "protobuf"
        self.cpp_info.names["cmake_find_package_multi"] = "protobuf"
        for name in ("libprotobuf-lite", "libprotobuf", "libprotoc"):
            self.cpp_info.components[name].names["cmake_find_package"] = name
            self.cpp_info.components[name].names["cmake_find_package_multi"] = name
