from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy


class MathutilsConan(ConanFile):
    name = "mathutils"
    version = "1.0.0"

    license = "MIT"
    description = (
        "Tiny math helper library + CLI tool used as a Conan 2 packaging demo"
    )
    settings = "os", "compiler", "build_type", "arch"

    # Ships both a shared library and an executable that links against it,
    # so VirtualRunEnv has something meaningful to set up at runtime
    # (PATH for the bin/ tool, LD_LIBRARY_PATH for the lib/ shared object).
    package_type = "application"

    exports_sources = "CMakeLists.txt", "include/*", "src/*"

    def layout(self):
        cmake_layout(self)

    def generate(self):
        toolchain = CMakeToolchain(self)
        toolchain.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["mathutils"]
