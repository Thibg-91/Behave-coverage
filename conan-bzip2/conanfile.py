from conan import ConanFile
from conan.tools.cmake import CMakeToolchain, CMakeDeps, cmake_layout


class BZip2Consumer(ConanFile):
    name = "bzip2-consumer"
    version = "1.0"
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # bzip2/1.0.8 dispose de binaires précompilés sur ConanCenter
        # pour MSVC 192 (Visual Studio 2019) — aucun --build=missing nécessaire.
        self.requires("bzip2/1.0.8")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # Génère les fichiers d'intégration CMake dans le dossier build
        tc = CMakeToolchain(self)
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()
