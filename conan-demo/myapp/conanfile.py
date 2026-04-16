import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import copy


class MyAppConan(ConanFile):
    name = "myapp"
    version = "1.0"
    description = "Simple executable that uses the mymath pre-built library."
    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"
    exports_sources = "CMakeLists.txt", "src/*"

    requires = "mymath/1.0"

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        """Copy the built executable into the Conan package folder (bin/)."""
        ext = ".exe" if self.settings.os == "Windows" else ""
        # copy() searches recursively: handles both single-config (Linux/Ninja)
        # and multi-config (Windows/MSVC) build layouts.
        copy(self, f"myapp{ext}",
             src=self.build_folder,
             dst=os.path.join(self.package_folder, "bin"),
             keep_path=False)

    def package_info(self):
        """Expose bin/ so VirtualRunEnv adds it to PATH."""
        self.cpp_info.bindirs = ["bin"]
