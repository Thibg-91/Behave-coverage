import json
import os
import re

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import check_sha256, copy, get, load, rmdir, save, unzip
from conan.tools.microsoft import is_msvc

required_conan_version = ">=1.60.0"


class AbseilConan(ConanFile):
    name = "abseil"
    description = "Abseil Common Libraries (C++) from Google"
    license = "Apache-2.0"
    url = "https://github.com/abseil/abseil-cpp"
    homepage = "https://abseil.io"
    topics = ("algorithm", "container", "google", "common", "utility")

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    # Archive des sources posee a cote de la recette (mode hors-ligne)
    exports_sources = "abseil-cpp-*.tar.gz"

    _components_file = os.path.join("lib", "conan", "abseil-components.json")

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

    def validate(self):
        # L'ABI d'abseil depend du standard C++ (absl::string_view est un alias
        # de std::string_view en C++17, un type maison en C++14). Il faut donc que
        # abseil, protobuf et l'application utilisent le MEME standard : on exige
        # qu'il soit fixe explicitement dans le profil.
        if not self.settings.compiler.get_safe("cppstd"):
            raise ConanInvalidConfiguration(
                f"{self.ref} : definis compiler.cppstd dans le profil (ex. 17). "
                "L'ABI d'abseil depend du standard C++ utilise."
            )
        check_min_cppstd(self, 14)
        if self.options.shared and is_msvc(self):
            raise ConanInvalidConfiguration(
                f"{self.ref} : la DLL abseil (abseil_dll) n'est pas geree par cette recette, "
                "utilise shared=False sous MSVC"
            )

    # ------------------------------------------------------------------ #
    # Sources : archive locale si presente, sinon telechargement
    # ------------------------------------------------------------------ #
    def source(self):
        archive_name = f"abseil-cpp-{self.version}.tar.gz"
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
        tc.variables["ABSL_ENABLE_INSTALL"] = True
        tc.variables["ABSL_PROPAGATE_CXX_STD"] = True
        tc.variables["ABSL_BUILD_TESTING"] = False
        tc.variables["ABSL_BUILD_TEST_HELPERS"] = False
        tc.variables["BUILD_TESTING"] = False
        tc.generate()

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
        cmake = CMake(self)
        cmake.install()

        # Avant de supprimer les fichiers CMake officiels, on en extrait la liste
        # des cibles absl::* et leurs dependances : c'est la source de verite.
        targets_file = os.path.join(self.package_folder, "lib", "cmake", "absl", "abslTargets.cmake")
        components = self._parse_targets(load(self, targets_file))
        save(self, os.path.join(self.package_folder, self._components_file),
             json.dumps(components, indent=2, sort_keys=True))

        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    @staticmethod
    def _parse_targets(content):
        """Transforme abslTargets.cmake en {composant: {type, requires, system_libs, frameworks}}.

        Les expressions generateur ecrites par CMake sont evaluees ici, a l'installation :
          $<LINK_ONLY:X>                 -> X
          $<$<BOOL:val>:-lfoo>           -> foo si val est vrai (ex. chemin de librt trouve)
          $<$<PLATFORM_ID:Darwin>:-Wl,-framework,F> -> framework F (macOS uniquement)
        """
        content = content.replace("\\$", "$")

        def is_true(value):
            v = value.strip().upper()
            return bool(v) and v not in ("0", "OFF", "FALSE", "NO", "N", "IGNORE") and not v.endswith("NOTFOUND")

        def evaluate(item):
            item = item.strip()
            while True:
                m = re.fullmatch(r"\$<LINK_ONLY:(.*)>", item)
                if not m:
                    break
                item = m.group(1)
            m = re.fullmatch(r"\$<\$<BOOL:([^>]*)>:(.*)>", item)
            if m:
                return [m.group(2)] if is_true(m.group(1)) else []
            m = re.fullmatch(r"\$<\$<PLATFORM_ID:Darwin>:(.*)>", item)
            if m:
                return ["darwin:" + m.group(1)]
            if item.startswith("$<"):
                return []  # autre expression generateur : ignoree
            return [item] if item else []

        components = {}
        for name, kind in re.findall(r"add_library\(absl::(\w+) (STATIC|SHARED|INTERFACE) IMPORTED\)", content):
            components[name] = {"type": kind, "requires": [], "system_libs": [], "frameworks": []}

        test_only = set()
        for name, props in re.findall(r"set_target_properties\(absl::(\w+) PROPERTIES(.*?)\n\)", content, re.S):
            if name not in components:
                continue
            m = re.search(r'INTERFACE_LINK_LIBRARIES "([^"]*)"', props)
            if not m:
                continue
            comp = components[name]
            for raw in m.group(1).split(";"):
                for item in evaluate(raw):
                    if item.startswith("absl::"):
                        comp["requires"].append(item[len("absl::"):])
                    elif item.startswith("GTest::"):
                        test_only.add(name)  # aide aux tests (gmock) : non exposee
                    elif item == "Threads::Threads":
                        comp["system_libs"].append("pthread")
                    elif item.startswith("darwin:-Wl,-framework,"):
                        comp["frameworks"].append(item[len("darwin:-Wl,-framework,"):])
                    elif item.startswith("-l"):
                        comp["system_libs"].append(item[2:])
                    elif not item.startswith("-") and not item.startswith("darwin:"):
                        comp["system_libs"].append(item)

        for name in test_only:
            components.pop(name, None)
        for comp in components.values():
            comp["requires"] = [r for r in comp["requires"] if r in components]
        return components

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "absl")
        self.cpp_info.set_property("cmake_target_name", "absl::absl")
        self.cpp_info.names["cmake_find_package"] = "absl"
        self.cpp_info.names["cmake_find_package_multi"] = "absl"

        components = json.loads(load(self, os.path.join(self.package_folder, self._components_file)))
        for name, info in components.items():
            comp = self.cpp_info.components[name]
            comp.set_property("cmake_target_name", f"absl::{name}")
            comp.names["cmake_find_package"] = name
            comp.names["cmake_find_package_multi"] = name
            if info["type"] != "INTERFACE":
                comp.libs = [f"absl_{name}"]
            comp.requires = sorted(set(info["requires"]))
            system_libs = set(info["system_libs"])
            if self.settings.os in ("Linux", "FreeBSD") and "pthread" in system_libs:
                system_libs.add("m")
            if self.settings.os not in ("Linux", "FreeBSD"):
                system_libs.discard("pthread")
                system_libs.discard("rt")
            comp.system_libs = sorted(system_libs)
            if self.settings.os == "Macos":
                comp.frameworks = sorted(set(info["frameworks"]))
